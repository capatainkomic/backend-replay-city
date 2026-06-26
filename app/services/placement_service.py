"""
Ce service prend la liste d'objets du LLM et calcule
les positions exactes de chaque objet dans le terrain.

Fonctionnement :
1. Pour chaque objet demandé par le LLM :
   - Recherche l'asset correspondant dans la bibliothèque
   - Si trouvé (similarité > 0.4) → utilise l'asset réel
   - Si non trouvé → crée un placeholder (boîte qui represente l'objet manquant)
2. Calcule les positions en respectant :
   - Les contraintes spatiales du LLM
   - Les bounding boxes des objets
   - Les rayons de sécurité
3. Gère la végétation répétitive avec un scatter algorithm
"""

import random
import math
from shapely.geometry import box, Point, Polygon
from shapely.affinity import rotate, translate
from app.services.library_service import rechercher_assets
from app.models.schemas import Object3D

# Seuil de similarité minimum pour utiliser un asset réel plutôt qu'un placeholder
SEUIL_SIMILARITE = 0.4

# Couleurs des placeholders par catégorie
COULEURS_PLACEHOLDER = {
    "equipement": "#ff9999",      # rouge clair
    "mobilier_urbain": "#99ccff", # bleu clair
    "vegetation": "#99ff99",      # vert clair
}


def placer_objets(
    objets_llm: list[dict],
    contraintes: list[dict],
    terrain_largeur_m: float,
    terrain_longueur_m: float,
    accessibilite_pmr: bool = False
) -> tuple[list[Object3D], list[str]]:
    """
    Place tous les objets dans le terrain.

    Args:
        objets_llm      : liste des objets demandés par le LLM
        contraintes     : contraintes spatiales entre objets
        terrain_largeur_m : largeur du terrain en mètres
        terrain_longueur_m : longueur du terrain en mètres
        accessibilite_pmr : si True, réserve des allées plus larges

    Returns:
        - liste d'Object3D positionnés
        - liste d'avertissements
    """

    avertissements = []
    objets_places = []

    # Zones déjà occupées — on les remplit au fur et à mesure
    # pour éviter les chevauchements
    zones_occupees = []

    # Marge intérieure du terrain (on ne place pas les objets
    # trop près des bords)
    marge = 1.0

    # 1. Pour chaque objet demandé par le LLM
    for objet_llm in objets_llm:
        quantite = objet_llm.get("quantite", 1)
        description = objet_llm.get("description_recherche", "")
        categorie = objet_llm.get("categorie", "equipement")
        priorite = objet_llm.get("priorite", "recommande")
        id_temp = objet_llm.get("id_temp", "")

        # 2. Recherche dans la bibliothèque
        resultats = rechercher_assets(
            description=description,
            categorie=categorie,
            limite=1
        )

        # 3. Asset trouvé ou placeholder ?
        if resultats and resultats[0]["similarite"] >= SEUIL_SIMILARITE:
            asset = resultats[0]
            est_placeholder = False
        else:
            # Pas de bon match → placeholder
            asset = _creer_asset_defaut(description, categorie)
            est_placeholder = True
            avertissements.append(
                f"Objet approximatif : '{description}' — placeholder utilisé"
            )

        # 4. Place le bon nombre d'instances
        for i in range(quantite):

            # Détermine la contrainte spatiale pour cet objet
            contrainte = _trouver_contrainte(id_temp, contraintes)

            # Calcule la position selon la contrainte
            position = _calculer_position(
                asset=asset,
                contrainte=contrainte,
                terrain_largeur_m=terrain_largeur_m,
                terrain_longueur_m=terrain_longueur_m,
                zones_occupees=zones_occupees,
                marge=marge,
                objets_places=objets_places
            )

            if position is None:
                avertissements.append(
                    f"Impossible de placer : '{description}' — terrain trop petit"
                )
                continue

            x, z, rotation = position

            # 5. Crée l'objet 3D
            if est_placeholder:
                objet_3d = Object3D(
                    asset_id="placeholder",
                    nom=f"{description} (à générer)",
                    type="placeholder",
                    fichier_glb=None,
                    placeholder_label=description,
                    placeholder_couleur=COULEURS_PLACEHOLDER.get(categorie, "#cccccc"),
                    scale_x=1.0,
                    scale_y=1.0,
                    scale_z=1.0,
                    position_x=x,
                    position_z=z,
                    position_y=0.0,
                    rotation_y=rotation,
                    largeur_m=asset["largeur_m"],
                    longueur_m=asset["longueur_m"],
                    hauteur_m=asset["hauteur_m"],
                    categorie=categorie,
                    similarite=None
                )
            else:
                objet_3d = Object3D(
                    asset_id=asset["id"],
                    nom=asset["nom"],
                    type="asset",
                    fichier_glb=asset["url_glb"],
                    placeholder_label=None,
                    placeholder_couleur=None,
                    scale_x=asset.get("scale_x", 1.0),
                    scale_y=asset.get("scale_y", 1.0),
                    scale_z=asset.get("scale_z", 1.0),
                    position_x=x,
                    position_z=z,
                    position_y=0.0,
                    rotation_y=rotation,
                    largeur_m=asset["largeur_m"],
                    longueur_m=asset["longueur_m"],
                    hauteur_m=asset["hauteur_m"],
                    categorie=categorie,
                    similarite=asset.get("similarite")
                )

            objets_places.append(objet_3d)

            # Ajoute la zone occupée par cet objet
            rayon = asset.get("rayon_securite_m", 0.5)
            zone = _creer_zone_occupee(
                x, z,
                asset["largeur_m"] + rayon * 2,
                asset["longueur_m"] + rayon * 2,
                rotation
            )
            zones_occupees.append(zone)

    return objets_places, avertissements


def _trouver_contrainte(id_temp: str, contraintes: list[dict]) -> dict | None:
    """
    Trouve la contrainte spatiale pour un objet donné.
    """
    for contrainte in contraintes:
        if contrainte.get("objet_1") == id_temp:
            return contrainte
    return None


def _calculer_position(
    asset: dict,
    contrainte: dict | None,
    terrain_largeur_m: float,
    terrain_longueur_m: float,
    zones_occupees: list,
    marge: float,
    objets_places: list
) -> tuple | None:
    """
    Calcule une position valide pour un objet.

    Stratégie :
    1. Détermine la zone cible selon la contrainte (centre, périmètre, entrée)
    2. Essaie des positions aléatoires dans cette zone
    3. Vérifie qu'il n'y a pas de chevauchement avec les zones déjà occupées
    4. Retourne la première position valide trouvée
    """

    largeur = asset["largeur_m"]
    longueur = asset["longueur_m"]
    rayon = asset.get("rayon_securite_m", 0.5)

    # Zone de placement selon la contrainte
    relation = contrainte.get("relation") if contrainte else None
    cible = contrainte.get("objet_2") if contrainte else None

    # Définition des zones de placement possibles
    # selon la relation spatiale
    if relation == "centre" or cible == "centre":
        # Tiers central du terrain
        x_min = terrain_largeur_m * 0.3
        x_max = terrain_largeur_m * 0.7
        z_min = terrain_longueur_m * 0.3
        z_max = terrain_longueur_m * 0.7

    elif relation == "borde" and cible == "perimetre":
        # Proche des bords
        # On choisit aléatoirement un côté
        cote = random.choice(["haut", "bas", "gauche", "droite"])
        if cote == "haut":
            x_min, x_max = marge, terrain_largeur_m - marge
            z_min, z_max = marge, terrain_longueur_m * 0.2
        elif cote == "bas":
            x_min, x_max = marge, terrain_largeur_m - marge
            z_min, z_max = terrain_longueur_m * 0.8, terrain_longueur_m - marge
        elif cote == "gauche":
            x_min, x_max = marge, terrain_largeur_m * 0.2
            z_min, z_max = marge, terrain_longueur_m - marge
        else:
            x_min, x_max = terrain_largeur_m * 0.8, terrain_largeur_m - marge
            z_min, z_max = marge, terrain_longueur_m - marge

    elif relation == "borde" and cible == "entree":
        # Proche de l'entrée (on considère l'entrée en bas du terrain)
        x_min = terrain_largeur_m * 0.3
        x_max = terrain_largeur_m * 0.7
        z_min = marge
        z_max = terrain_longueur_m * 0.3

    else:
        # Pas de contrainte → placement libre
        x_min = marge + largeur / 2
        x_max = terrain_largeur_m - marge - largeur / 2
        z_min = marge + longueur / 2
        z_max = terrain_longueur_m - marge - longueur / 2

    # Rotation aléatoire parmi des angles standards
    rotations_possibles = [0, 45, 90, 135, 180, 225, 270, 315]

    # Essais de placement (100 tentatives max)
    for _ in range(100):
        x = random.uniform(
            max(x_min, marge + largeur / 2),
            min(x_max, terrain_largeur_m - marge - largeur / 2)
        )
        z = random.uniform(
            max(z_min, marge + longueur / 2),
            min(z_max, terrain_longueur_m - marge - longueur / 2)
        )
        rotation = random.choice(rotations_possibles)

        # Vérifie qu'il n'y a pas de chevauchement
        zone_candidate = _creer_zone_occupee(
            x, z,
            largeur + rayon * 2,
            longueur + rayon * 2,
            rotation
        )

        if not _chevauche(zone_candidate, zones_occupees):
            return x, z, rotation

    # Aucune position valide trouvée
    return None


def _creer_zone_occupee(
    x: float,
    z: float,
    largeur: float,
    longueur: float,
    rotation: float
) -> Polygon:
    """
    Crée un polygone Shapely représentant la zone occupée par un objet.
    Tient compte de la rotation.
    """
    # Crée un rectangle centré en (0, 0)
    rect = box(-largeur / 2, -longueur / 2, largeur / 2, longueur / 2)

    # Applique la rotation
    rect_rotated = rotate(rect, rotation, origin=(0, 0))

    # Déplace au bon endroit
    rect_final = translate(rect_rotated, x, z)

    return rect_final


def _chevauche(zone: Polygon, zones_occupees: list) -> bool:
    """
    Vérifie si une zone chevauche une zone déjà occupée.
    """
    for zone_existante in zones_occupees:
        if zone.intersects(zone_existante):
            return True
    return False


def _creer_asset_defaut(description: str, categorie: str) -> dict:
    """
    Crée un asset par défaut pour les placeholders.
    Dimensions standard selon la catégorie.
    """
    dimensions_defaut = {
        "equipement":     {"largeur_m": 2.0, "longueur_m": 2.0, "hauteur_m": 2.0, "rayon_securite_m": 1.5},
        "mobilier_urbain": {"largeur_m": 1.0, "longueur_m": 0.5, "hauteur_m": 1.0, "rayon_securite_m": 0.5},
        "vegetation":     {"largeur_m": 1.5, "longueur_m": 1.5, "hauteur_m": 3.0, "rayon_securite_m": 0.5},
    }

    dims = dimensions_defaut.get(categorie, dimensions_defaut["equipement"])

    return {
        "id": "placeholder",
        "nom": description,
        "description": description,
        "categorie": categorie,
        "url_glb": None,
        "scale_x": 1.0,
        "scale_y": 1.0,
        "scale_z": 1.0,
        "similarite": 0.0,
        **dims
    }