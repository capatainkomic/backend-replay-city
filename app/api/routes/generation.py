"""
Endpoint principal qui orchestre tout le pipeline :
1. Reçoit le formulaire
2. Normalise le terrain
3. Appelle le LLM pour la liste d'objets
4. Place les objets avec Shapely
5. Sauvegarde en base
6. Retourne la SceneResponse
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.schemas import GenerationRequest, SceneResponse
from app.services.llm_service import generer_liste_objets
from app.services.placement_service import placer_objets
from app.core.database import supabase
from shapely.geometry import shape
import uuid
import json
from datetime import datetime

router = APIRouter(prefix="/api/v1/generation", tags=["Génération 3D"])


def normaliser_terrain(request: GenerationRequest) -> tuple[float, float]:
    """
    Normalise le terrain en largeur et longueur en mètres.
    Gère les deux cas : rectangle et GeoJSON.
    """
    if request.terrain_shape.value == "rectangle":
        return (
            request.terrain_rectangle.largeur_m,
            request.terrain_rectangle.longueur_m
        )
    elif request.terrain_shape.value == "geojson":
        # Calcule les dimensions depuis le GeoJSON
        polygon = shape(request.terrain_geojson.geojson)
        bounds = polygon.bounds
        # bounds = (minx, miny, maxx, maxy)
        largeur = bounds[2] - bounds[0]
        longueur = bounds[3] - bounds[1]
        return largeur, longueur
    else:
        raise HTTPException(
            status_code=400,
            detail="Format de terrain non supporté"
        )


def calculer_metriques(
    objets_places: list,
    terrain_largeur_m: float,
    terrain_longueur_m: float
) -> dict:
    """
    Calcule les métriques de la scène pour la comparaison de projets.
    """
    terrain_surface = terrain_largeur_m * terrain_longueur_m

    # Surface occupée par les objets
    surface_occupee = sum(
        obj.largeur_m * obj.longueur_m
        for obj in objets_places
    )

    surface_pct = round((surface_occupee / terrain_surface) * 100, 1)

    # Détail par catégorie
    nb_par_categorie = {}
    for obj in objets_places:
        cat = obj.categorie
        nb_par_categorie[cat] = nb_par_categorie.get(cat, 0) + 1

    return {
        "nb_objets": len(objets_places),
        "surface_occupee_m2": round(surface_occupee, 2),
        "surface_occupee_pct": min(surface_pct, 100.0),
        "nb_objets_par_categorie": nb_par_categorie,
    }


@router.post(
    "/",
    response_model=SceneResponse,
    summary="Générer une maquette 3D",
    description="Pipeline complet : LLM → recherche sémantique → placement → scène 3D"
)
async def generate_scene(request: GenerationRequest):
    """
    Pipeline principal de génération de maquette 3D.
    """

    # ── ÉTAPE 1 : Normalisation du terrain ──
    terrain_largeur_m, terrain_longueur_m = normaliser_terrain(request)

    # ── ÉTAPE 2 : Appel au LLM ──
    print(f"🤖 Appel LLM pour projet {request.project_type}...")
    resultat_llm = generer_liste_objets(
        project_type=request.project_type.value,
        terrain_largeur_m=terrain_largeur_m,
        terrain_longueur_m=terrain_longueur_m,
        age_ranges=[age.value for age in request.age_ranges],
        accessibilite_pmr=request.accessibilite_pmr,
        description_libre=request.project_description
    )

    objets_llm = resultat_llm.get("objets", [])
    contraintes = resultat_llm.get("contraintes", [])

    print(f"📋 LLM a proposé {len(objets_llm)} objets")

    if not objets_llm:
        raise HTTPException(
            status_code=500,
            detail="Le LLM n'a pas pu générer de liste d'objets"
        )

    # ── ÉTAPE 3 : Placement des objets ──
    print("📐 Calcul du placement...")
    objets_places, avertissements = placer_objets(
        objets_llm=objets_llm,
        contraintes=contraintes,
        terrain_largeur_m=terrain_largeur_m,
        terrain_longueur_m=terrain_longueur_m,
        accessibilite_pmr=request.accessibilite_pmr
    )

    print(f"✅ {len(objets_places)} objets placés")

    # ── ÉTAPE 4 : Calcul des métriques ──
    metriques = calculer_metriques(
        objets_places,
        terrain_largeur_m,
        terrain_longueur_m
    )

    # ── ÉTAPE 5 : Construction de la réponse ──
    scene_id = str(uuid.uuid4())

    scene_response = SceneResponse(
        scene_id=scene_id,
        objets=objets_places,
        terrain_largeur_m=terrain_largeur_m,
        terrain_longueur_m=terrain_longueur_m,
        nb_objets_total=metriques["nb_objets"],
        surface_occupee_pct=metriques["surface_occupee_pct"],
        conforme_normes=len(avertissements) == 0,
        avertissements=avertissements
    )

    # ── ÉTAPE 6 : Sauvegarde en base ──
    try:
        # Détermine le type et les données du terrain
        if request.terrain_shape.value == "rectangle":
            terrain_data = {
                "longueur_m": terrain_longueur_m,
                "largeur_m": terrain_largeur_m
            }
        else:
            terrain_data = request.terrain_geojson.geojson

        # Convertit les objets en JSON sérialisable
        scene_json = json.loads(scene_response.model_dump_json())

        supabase.table("projets").insert({
            "id": scene_id,
            "terrain_type": request.terrain_shape.value,
            "terrain_data": terrain_data,
            "terrain_surface_m2": round(terrain_largeur_m * terrain_longueur_m, 2),
            "project_type": request.project_type.value,
            "description_libre": request.project_description,
            "age_ranges": [age.value for age in request.age_ranges],
            "accessibilite_pmr": request.accessibilite_pmr,
            "scene_json": scene_json,
            "nb_objets": metriques["nb_objets"],
            "nb_objets_par_categorie": metriques["nb_objets_par_categorie"],
            "nb_objets_par_age": {},
            "surface_occupee_m2": metriques["surface_occupee_m2"],
            "surface_occupee_pct": metriques["surface_occupee_pct"],
            "estimation_prix_min_euros": 0.0,
            "estimation_prix_max_euros": 0.0,
            "placement_coherent": len(avertissements) == 0,
            "avertissements": avertissements,
        }).execute()

        print(f"💾 Projet sauvegardé — ID : {scene_id}")

    except Exception as e:
        # La sauvegarde échoue → on retourne quand même la scène
        # L'historique est perdu mais le client a son résultat
        print(f"⚠️ Erreur sauvegarde : {e}")
        avertissements.append("Avertissement : projet non sauvegardé en base")

    return scene_response