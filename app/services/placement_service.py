"""
Pipeline de placement en couches :
Couche 1 : Focaux (au centre de leur zone)
Couche 2 : Relationnels (près des focaux)
Couche 3 : Distributifs (Poisson Disk Sampling)
Couche 4 : Ponctuels (placement libre)
"""

import random
import math
from shapely.geometry import box, Point, Polygon
from shapely.affinity import rotate, translate
from app.services.library_service import rechercher_assets
from app.models.schemas import Object3D

SEUIL_SIMILARITE = 0.35

COULEURS_PLACEHOLDER = {
    "equipement":      "#ff9999",
    "mobilier_urbain": "#99ccff",
    "vegetation":      "#99ff99",
}

# Ordre de traitement par placement_type
ORDRE_PLACEMENT = ["focal", "relationnel", "distributif", "ponctuel"]


def placer_objets(
    objets_llm: list[dict],
    contraintes: list[dict],
    terrain_largeur_m: float,
    terrain_longueur_m: float,
    accessibilite_pmr: bool = False
) -> tuple[list[Object3D], list[str]]:

    avertissements = []
    objets_places = []
    zones_occupees = []
    marge = 0.5

    # Tri : priorité indispensable d'abord, puis par type de placement
    ordre_priorite = {"indispensable": 0, "recommande": 1, "bonus": 2}

    def cle_tri(obj):
        asset = _trouver_asset(obj)
        placement_type = asset.get("placement_type", "ponctuel") if asset else "ponctuel"
        type_ordre = ORDRE_PLACEMENT.index(placement_type) if placement_type in ORDRE_PLACEMENT else 4
        return (ordre_priorite.get(obj.get("priorite", "bonus"), 2), type_ordre)

    objets_tries = sorted(objets_llm, key=cle_tri)

    # Garde une map des derniers focaux placés par zone
    # pour que les relationnels sachent où se positionner
    derniers_focaux_par_zone = {}

    for objet_llm in objets_tries:
        quantite = objet_llm.get("quantite", 1)
        description = objet_llm.get("description_recherche", "")
        categorie = objet_llm.get("categorie", "equipement")
        id_temp = objet_llm.get("id_temp", "")
        zone_id = objet_llm.get("zone_id", "")

        # Recherche dans la bibliothèque
        resultats = rechercher_assets(
            description=description,
            categorie=categorie,
            limite=1
        )

        if resultats and resultats[0]["similarite"] >= SEUIL_SIMILARITE:
            asset = resultats[0]
            est_placeholder = False
        else:
            asset = _creer_asset_defaut(description, categorie)
            est_placeholder = True
            avertissements.append(
                f"Objet approximatif : '{description}' — placeholder utilisé"
            )

        placement_type = asset.get("placement_type", "ponctuel")

        for i in range(quantite):
            position = _calculer_position_par_type(
                asset=asset,
                placement_type=placement_type,
                objet_llm=objet_llm,
                terrain_largeur_m=terrain_largeur_m,
                terrain_longueur_m=terrain_longueur_m,
                zones_occupees=zones_occupees,
                marge=marge,
                dernier_focal=derniers_focaux_par_zone.get(zone_id),
                index_instance=i
            )

            if position is None:
                avertissements.append(
                    f"Impossible de placer : '{description}' — terrain trop petit"
                )
                continue

            x, z, rotation = position

            # Crée l'objet 3D
            objet_3d = _creer_objet_3d(
                asset=asset,
                est_placeholder=est_placeholder,
                description=description,
                categorie=categorie,
                x=x, z=z,
                rotation=rotation
            )

            objets_places.append(objet_3d)

            # Met à jour le dernier focal de cette zone
            if placement_type == "focal":
                derniers_focaux_par_zone[zone_id] = (x, z)

            # Rayon réduit selon le type pour éviter les espaces vides
            rayon = _rayon_effectif(asset, placement_type)
            zone = _creer_zone_occupee(
                x, z,
                asset["largeur_m"] + rayon * 2,
                asset["longueur_m"] + rayon * 2,
                rotation
            )
            zones_occupees.append(zone)

    return objets_places, avertissements


# ─────────────────────────────────────────────
# PLACEMENT PAR TYPE
# ─────────────────────────────────────────────

def _calculer_position_par_type(
    asset, placement_type, objet_llm,
    terrain_largeur_m, terrain_longueur_m,
    zones_occupees, marge, dernier_focal, index_instance
):
    """Dispatch vers la bonne stratégie selon le type."""

    if placement_type == "focal":
        return _placer_focal(asset, objet_llm, terrain_largeur_m, terrain_longueur_m, zones_occupees, marge)

    elif placement_type == "relationnel":
        return _placer_relationnel(asset, objet_llm, terrain_largeur_m, terrain_longueur_m, zones_occupees, marge, dernier_focal, index_instance)

    elif placement_type == "distributif":
        return _placer_distributif(asset, objet_llm, terrain_largeur_m, terrain_longueur_m, zones_occupees, marge)

    else:  # ponctuel
        return _placer_ponctuel(asset, objet_llm, terrain_largeur_m, terrain_longueur_m, zones_occupees, marge)


def _placer_focal(asset, objet_llm, terrain_largeur_m, terrain_longueur_m, zones_occupees, marge):
    """
    Place au centre de sa zone.
    Un focal structure la zone autour de lui.
    """
    if "zone_x_debut" in objet_llm:
        zx = objet_llm["zone_x_debut"]
        zz = objet_llm["zone_z_debut"]
        zw = objet_llm["zone_largeur"]
        zl = objet_llm["zone_longueur"]

        # Centre de la zone
        cx = zx + zw / 2
        cz = zz + zl / 2

        # Essaie d'abord le centre exact, puis s'éloigne progressivement
        for rayon_recherche in [0, 0.5, 1.0, 1.5, 2.0, 3.0]:
            for _ in range(20):
                if rayon_recherche == 0:
                    x, z = cx, cz
                else:
                    angle = random.uniform(0, 2 * math.pi)
                    x = cx + math.cos(angle) * rayon_recherche
                    z = cz + math.sin(angle) * rayon_recherche

                # Reste dans la zone
                x = max(zx + asset["largeur_m"]/2 + marge,
                        min(x, zx + zw - asset["largeur_m"]/2 - marge))
                z = max(zz + asset["longueur_m"]/2 + marge,
                        min(z, zz + zl - asset["longueur_m"]/2 - marge))

                rotation = random.choice([0, 90, 180, 270])
                zone_candidate = _creer_zone_occupee(
                    x, z, asset["largeur_m"], asset["longueur_m"], rotation
                )
                if not _chevauche(zone_candidate, zones_occupees):
                    return x, z, rotation

    return _placer_ponctuel(asset, objet_llm, terrain_largeur_m, terrain_longueur_m, zones_occupees, marge)


def _placer_relationnel(asset, objet_llm, terrain_largeur_m, terrain_longueur_m, zones_occupees, marge, dernier_focal, index_instance):
    """
    Place près du dernier focal de la même zone.
    Les bancs/tables se mettent autour des équipements.
    """
    if dernier_focal:
        fx, fz = dernier_focal

        # Distance de placement selon l'index (0=gauche, 1=droite, 2=devant, 3=derrière)
        distances = [2.0, 2.5, 3.0, 3.5, 4.0]
        angles_preferes = [
            index_instance * (math.pi / 2),
            index_instance * (math.pi / 2) + math.pi / 4,
            index_instance * (math.pi / 2) - math.pi / 4,
        ]

        for dist in distances:
            for angle in angles_preferes:
                x = fx + math.cos(angle) * dist
                z = fz + math.sin(angle) * dist

                # Contraint au terrain
                x = max(marge + asset["largeur_m"]/2,
                        min(x, terrain_largeur_m - marge - asset["largeur_m"]/2))
                z = max(marge + asset["longueur_m"]/2,
                        min(z, terrain_longueur_m - marge - asset["longueur_m"]/2))

                # Rotation face au focal
                angle_vers_focal = math.atan2(fz - z, fx - x)
                rotation = round(math.degrees(angle_vers_focal) / 45) * 45 % 360

                zone_candidate = _creer_zone_occupee(
                    x, z, asset["largeur_m"], asset["longueur_m"], rotation
                )
                if not _chevauche(zone_candidate, zones_occupees):
                    return x, z, rotation

    # Fallback si pas de focal
    return _placer_ponctuel(asset, objet_llm, terrain_largeur_m, terrain_longueur_m, zones_occupees, marge)


def _placer_distributif(asset, objet_llm, terrain_largeur_m, terrain_longueur_m, zones_occupees, marge):
    """
    Poisson Disk Sampling dans la zone.
    Pour végétation et objets répétitifs.
    Distance minimale = bounding box + petit espacement naturel.
    """
    if "zone_x_debut" in objet_llm:
        zx = objet_llm["zone_x_debut"]
        zz = objet_llm["zone_z_debut"]
        zw = objet_llm["zone_largeur"]
        zl = objet_llm["zone_longueur"]

        dist_min = max(asset["largeur_m"], asset["longueur_m"]) * 1.2

        x_min = zx + asset["largeur_m"]/2 + marge
        x_max = zx + zw - asset["largeur_m"]/2 - marge
        z_min = zz + asset["longueur_m"]/2 + marge
        z_max = zz + zl - asset["longueur_m"]/2 - marge

        if x_min >= x_max or z_min >= z_max:
            return _placer_ponctuel(asset, objet_llm, terrain_largeur_m, terrain_longueur_m, zones_occupees, marge)

        # Poisson Disk : essaie des positions dans l'anneau autour des points existants
        for _ in range(100):
            x = random.uniform(x_min, x_max)
            z = random.uniform(z_min, z_max)
            rotation = random.uniform(0, 360)

            zone_candidate = _creer_zone_occupee(
                x, z,
                asset["largeur_m"] + dist_min,
                asset["longueur_m"] + dist_min,
                rotation
            )
            if not _chevauche(zone_candidate, zones_occupees):
                return x, z, rotation

    return None


def _placer_ponctuel(asset, objet_llm, terrain_largeur_m, terrain_longueur_m, zones_occupees, marge):
    """Placement libre dans la zone, sans logique particulière."""

    if "zone_x_debut" in objet_llm:
        zx = objet_llm["zone_x_debut"]
        zz = objet_llm["zone_z_debut"]
        zw = objet_llm["zone_largeur"]
        zl = objet_llm["zone_longueur"]

        x_min = zx + asset["largeur_m"]/2 + marge
        x_max = zx + zw - asset["largeur_m"]/2 - marge
        z_min = zz + asset["longueur_m"]/2 + marge
        z_max = zz + zl - asset["longueur_m"]/2 - marge
    else:
        x_min = marge + asset["largeur_m"]/2
        x_max = terrain_largeur_m - marge - asset["largeur_m"]/2
        z_min = marge + asset["longueur_m"]/2
        z_max = terrain_longueur_m - marge - asset["longueur_m"]/2

    if x_min >= x_max or z_min >= z_max:
        return None

    for _ in range(200):
        x = random.uniform(x_min, x_max)
        z = random.uniform(z_min, z_max)
        rotation = random.choice([0, 45, 90, 135, 180, 225, 270, 315])

        zone_candidate = _creer_zone_occupee(
            x, z, asset["largeur_m"], asset["longueur_m"], rotation
        )
        if not _chevauche(zone_candidate, zones_occupees):
            return x, z, rotation

    return None


# ─────────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────────

def _trouver_asset(objet_llm: dict) -> dict | None:
    """Cherche l'asset correspondant pour le tri initial."""
    try:
        resultats = rechercher_assets(
            description=objet_llm.get("description_recherche", ""),
            categorie=objet_llm.get("categorie", "equipement"),
            limite=1
        )
        if resultats and resultats[0]["similarite"] >= SEUIL_SIMILARITE:
            return resultats[0]
    except:
        pass
    return None


def _rayon_effectif(asset: dict, placement_type: str) -> float:
    """
    Rayon de sécurité réduit selon le type.
    Les distributifs et ponctuels ont un rayon minimal
    pour éviter les espaces vides.
    """
    rayon_base = asset.get("rayon_securite_m", 0.5)
    if placement_type in ["distributif", "ponctuel"]:
        return min(rayon_base, 0.3)
    return rayon_base


def _creer_objet_3d(asset, est_placeholder, description, categorie, x, z, rotation) -> Object3D:
    if est_placeholder:
        return Object3D(
            asset_id="placeholder",
            nom=f"{description} (à générer)",
            type="placeholder",
            fichier_glb=None,
            placeholder_label=description,
            placeholder_couleur=COULEURS_PLACEHOLDER.get(categorie, "#cccccc"),
            scale_x=1.0, scale_y=1.0, scale_z=1.0,
            position_x=x, position_z=z, position_y=0.0,
            rotation_y=rotation,
            largeur_m=asset["largeur_m"],
            longueur_m=asset["longueur_m"],
            hauteur_m=asset["hauteur_m"],
            categorie=categorie,
            similarite=None
        )
    else:
        return Object3D(
            asset_id=asset["id"],
            nom=asset["nom"],
            type="asset",
            fichier_glb=asset["url_glb"],
            placeholder_label=None,
            placeholder_couleur=None,
            scale_x=asset.get("scale_x", 1.0),
            scale_y=asset.get("scale_y", 1.0),
            scale_z=asset.get("scale_z", 1.0),
            position_x=x, position_z=z, position_y=0.0,
            rotation_y=rotation,
            largeur_m=asset["largeur_m"],
            longueur_m=asset["longueur_m"],
            hauteur_m=asset["hauteur_m"],
            categorie=categorie,
            similarite=asset.get("similarite")
        )


def _creer_zone_occupee(x, z, largeur, longueur, rotation) -> Polygon:
    rect = box(-largeur/2, -longueur/2, largeur/2, longueur/2)
    rect_rotated = rotate(rect, rotation, origin=(0, 0))
    return translate(rect_rotated, x, z)


def _chevauche(zone: Polygon, zones_occupees: list) -> bool:
    for zone_existante in zones_occupees:
        if zone.intersects(zone_existante):
            return True
    return False


def _creer_asset_defaut(description: str, categorie: str) -> dict:
    dimensions = {
        "equipement":      {"largeur_m": 2.0, "longueur_m": 2.0, "hauteur_m": 2.0, "rayon_securite_m": 1.5},
        "mobilier_urbain": {"largeur_m": 1.0, "longueur_m": 0.5, "hauteur_m": 1.0, "rayon_securite_m": 0.5},
        "vegetation":      {"largeur_m": 1.0, "longueur_m": 1.0, "hauteur_m": 2.0, "rayon_securite_m": 0.3},
    }
    dims = dimensions.get(categorie, dimensions["equipement"])
    return {
        "id": "placeholder",
        "nom": description,
        "description": description,
        "categorie": categorie,
        "url_glb": None,
        "scale_x": 1.0, "scale_y": 1.0, "scale_z": 1.0,
        "placement_type": "ponctuel",
        "similarite": 0.0,
        **dims
    }