"""
Endpoint principal qui orchestre tout le pipeline :
1. Reçoit le formulaire
2. Normalise le terrain
3. Appelle le LLM pour la liste d'objets
4. Place les objets avec Shapely
5. Sauvegarde en base
6. Retourne la SceneResponse
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import GenerationRequest, SceneResponse, Generation2DResponse, EquipementItem
from app.services.llm_service import generer_liste_objets, generer_metriques_2d
from app.services.placement_service import placer_objets
from app.services.image_service import generer_image_2d, analyser_image_equipements
from app.core.database import supabase
from shapely.geometry import shape
import uuid
import json

router = APIRouter(prefix="/api/v1/generation", tags=["Génération 3D"])


def normaliser_terrain(request: GenerationRequest) -> tuple[float, float]:
    if request.terrain_shape.value == "rectangle":
        return (
            request.terrain_rectangle.largeur_m,
            request.terrain_rectangle.longueur_m
        )
    elif request.terrain_shape.value == "geojson":
        polygon = shape(request.terrain_geojson.geojson)
        bounds = polygon.bounds
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
    terrain_surface = terrain_largeur_m * terrain_longueur_m
    surface_occupee = sum(
        obj.largeur_m * obj.longueur_m
        for obj in objets_places
    )
    surface_pct = round((surface_occupee / terrain_surface) * 100, 1)
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


# ─────────────────────────────────────────────
# ENDPOINT 3D
# ─────────────────────────────────────────────

@router.post(
    "/",
    response_model=SceneResponse,
    summary="Générer une maquette 3D",
    description="Pipeline complet : LLM → recherche sémantique → placement → scène 3D"
)
async def generate_scene(request: GenerationRequest):

    # Étape 1 : Normalisation du terrain
    terrain_largeur_m, terrain_longueur_m = normaliser_terrain(request)

    # Étape 2 : Appel au LLM
    print(f"Appel LLM pour projet {request.project_type}...")
    resultat_llm = generer_liste_objets(
        project_type=request.project_type.value,
        terrain_largeur_m=terrain_largeur_m,
        terrain_longueur_m=terrain_longueur_m,
        age_ranges=[age.value for age in request.age_ranges],
        budget_euros=request.budget_euros
    )

    objets_llm = resultat_llm.get("objets", [])
    contraintes = resultat_llm.get("contraintes", [])

    print(f"LLM a proposé {len(objets_llm)} objets")

    if not objets_llm:
        raise HTTPException(
            status_code=500,
            detail="Le LLM n'a pas pu générer de liste d'objets"
        )

    # Étape 3 : Placement des objets
    print("Calcul du placement...")
    objets_places, avertissements = placer_objets(
        objets_llm=objets_llm,
        contraintes=contraintes,
        terrain_largeur_m=terrain_largeur_m,
        terrain_longueur_m=terrain_longueur_m
    )

    print(f"{len(objets_places)} objets placés")

    # Étape 4 : Calcul des métriques
    metriques = calculer_metriques(
        objets_places,
        terrain_largeur_m,
        terrain_longueur_m
    )

    # Étape 5 : Construction de la réponse
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

    # Étape 6 : Sauvegarde en base
    try:
        if request.terrain_shape.value == "rectangle":
            terrain_data = {
                "longueur_m": terrain_longueur_m,
                "largeur_m": terrain_largeur_m
            }
        else:
            terrain_data = request.terrain_geojson.geojson

        scene_json = json.loads(scene_response.model_dump_json())

        supabase.table("projets").insert({
            "id": scene_id,
            "nom": request.project_name,
            "terrain_type": request.terrain_shape.value,
            "terrain_data": terrain_data,
            "terrain_surface_m2": round(terrain_largeur_m * terrain_longueur_m, 2),
            "project_type": request.project_type.value,
            "age_ranges": [age.value for age in request.age_ranges],
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

        print(f"Projet sauvegardé — ID : {scene_id}")

    except Exception as e:
        print(f"Erreur sauvegarde : {e}")
        avertissements.append("Avertissement : projet non sauvegardé en base")

    return scene_response


# ─────────────────────────────────────────────
# ENDPOINT 2D
# ─────────────────────────────────────────────

@router.post("/2d", response_model=Generation2DResponse)
async def generate_image_2d(request: GenerationRequest):

    terrain_largeur_m, terrain_longueur_m = normaliser_terrain(request)

    # 1. Génère l'image
    print("Génération de l'image 2D...")
    url_image = generer_image_2d(
        project_type=request.project_type.value,
        terrain_largeur_m=terrain_largeur_m,
        terrain_longueur_m=terrain_longueur_m,
        age_ranges=[age.value for age in request.age_ranges],
        budget_euros=request.budget_euros
    )

    if not url_image:
        raise HTTPException(status_code=500, detail="Erreur lors de la génération de l'image")

    # 2. Analyse l'image pour extraire les équipements
    print("Analyse des équipements...")
    metriques = analyser_image_equipements(
        url_image=url_image,
        budget_euros=request.budget_euros
    )

    equipements = [
        EquipementItem(
            nom=eq.get("nom", "Équipement"),
            quantite=eq.get("quantite", 1)
        )
        for eq in metriques.get("equipements", [])
    ]

    return Generation2DResponse(
        url_image=url_image,
        terrain_largeur_m=terrain_largeur_m,
        terrain_longueur_m=terrain_longueur_m,
        project_type=request.project_type.value,
        surface_occupee_pct=metriques.get("surface_occupee_pct", 70.0),
        cout_estime_euros=metriques.get("cout_total_euros", 0.0),
        equipements=equipements
    )