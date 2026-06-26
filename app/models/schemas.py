from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ─────────────────────────────────────────────
# LES ENUMS
# ─────────────────────────────────────────────


class ProjectType(str, Enum):
    """Types de projets supportés."""
    AIRE_DE_JEUX       = "aire_de_jeux"
    JARDIN_PEDAGOGIQUE = "jardin_pedagogique"
    ESPACE_LECTURE     = "espace_lecture"
    ESPACE_SPORTIF     = "espace_sportif"


class AgeRange(str, Enum):
    """Tranches d'âge cibles."""
    TOUT_PETITS = "0-3"
    MATERNELLE  = "3-6"
    PRIMAIRE    = "6-12"
    ADOS        = "12-18"
    MIXTE       = "mixte"


class TerrainShape(str, Enum):
    """Format dans lequel le terrain est fourni."""
    RECTANGLE = "rectangle"
    GEOJSON   = "geojson"


# ─────────────────────────────────────────────
# LE TERRAIN
# ─────────────────────────────────────────────

class TerrainRectangle(BaseModel):
    """
    Terrain fourni sous forme de rectangle simple.
    Le frontend envoie juste longueur et largeur en mètres.
    """
    longueur_m: float = Field(
        ...,        # '...' = ce champ est OBLIGATOIRE
        gt=0,       
        description="Longueur du terrain en mètres"
    )
    largeur_m: float = Field(
        ...,
        gt=0,
        description="Largeur du terrain en mètres"
    )


class TerrainGeoJSON(BaseModel):
    """
    Terrain fourni sous forme de GeoJSON (polygone précis).
    """
    geojson: dict = Field(
        ...,
        description="Objet GeoJSON de type Polygon"
    )


# ─────────────────────────────────────────────
# REQUÊTE du frontend
# ─────────────────────────────────────────────

class GenerationRequest(BaseModel):
    """
    Le formulaire complet que l'utilisateur remplit.
    Tout ce que le frontend envoie pour déclencher une génération.
    """

    # Le terrain
    terrain_shape: TerrainShape = Field(
        ...,
        description="Format du terrain : rectangle ou geojson"
    )
    terrain_rectangle: Optional[TerrainRectangle] = Field(
        None,       # None = pas obligatoire
        description="Dimensions si le terrain est un rectangle"
    )
    terrain_geojson: Optional[TerrainGeoJSON] = Field(
        None,
        description="GeoJSON si le terrain est un polygone précis"
    )

    # Le projet
    project_type: ProjectType = Field(
        ...,
        description="Type de projet à générer"
    )
    project_description: Optional[str] = Field(
        None,
        max_length=500,
        description="Description libre optionnelle du projet"
    )

    # Les contraintes
    age_ranges: list[AgeRange] = Field(
        ...,
        min_length=1,
        description="Tranches d'âge ciblées"
    )
    accessibilite_pmr: bool = Field(
        False,
        description="Le projet doit-il être accessible PMR ?"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "terrain_shape": "rectangle",
                "terrain_rectangle": {
                    "longueur_m": 30.0,
                    "largeur_m": 20.0
                },
                "project_type": "aire_de_jeux",
                "project_description": "Aire de jeux sur le thème de la forêt",
                "age_ranges": ["3-6", "6-12"],
                "accessibilite_pmr": True
            }
        }


# ─────────────────────────────────────────────
# UN OBJET 3D — un élément dans la scène
# ─────────────────────────────────────────────

class Object3D(BaseModel):
    """
    Représente un objet 3D positionné dans la scène.
    Peut être un vrai asset GLB ou un placeholder (boîte grise).
    """

    # Identification
    asset_id: str = Field(..., description="ID unique dans la bibliothèque ou 'placeholder'")
    nom: str = Field(..., description="Nom lisible de l'objet")

    # Type d'objet
    # 'asset' = vrai modèle 3D disponible
    # 'placeholder' = boîte grise avec label (objet manquant)
    type: str = Field("asset", description="'asset' ou 'placeholder'")

    # Fichier 3D — null si placeholder
    fichier_glb: Optional[str] = Field(None, description="URL du fichier .glb")

    # Informations placeholder
    placeholder_label: Optional[str] = Field(
        None,
        description="Nom affiché sur la boîte grise si placeholder"
    )
    placeholder_couleur: Optional[str] = Field(
        "#cccccc",
        description="Couleur de la boîte placeholder en hex"
    )

    # Scale à appliquer dans Three.js
    scale_x: float = Field(1.0, description="Scale axe X")
    scale_y: float = Field(1.0, description="Scale axe Y")
    scale_z: float = Field(1.0, description="Scale axe Z")

    # Position en mètres
    position_x: float = Field(..., description="Position horizontale en mètres")
    position_z: float = Field(..., description="Position en profondeur en mètres")
    position_y: float = Field(0.0, description="Hauteur (0 = au sol)")

    # Rotation en degrés
    rotation_y: float = Field(0.0, ge=0, lt=360, description="Rotation en degrés")

    # Dimensions réelles (bounding box)
    largeur_m: float = Field(..., description="Largeur réelle en mètres")
    longueur_m: float = Field(..., description="Longueur réelle en mètres")
    hauteur_m: float = Field(..., description="Hauteur réelle en mètres")

    # Catégorie
    categorie: str = Field(..., description="equipement, vegetation, mobilier_urbain")

    # Score de similarité avec la recherche sémantique
    similarite: Optional[float] = Field(
        None,
        description="Score de correspondance avec la bibliothèque (0 à 1)"
    )


# ─────────────────────────────────────────────
# Reponse du backend 
# ─────────────────────────────────────────────

class SceneResponse(BaseModel):
    """
    La réponse complète après génération.
    Le frontend lit ce JSON pour construire la scène 3D.
    """

    scene_id: str = Field(..., description="ID unique de cette scène")
    objets: list[Object3D] = Field(..., description="Tous les objets positionnés")

    # Dimensions du terrain
    terrain_largeur_m: float = Field(..., description="Largeur en mètres")
    terrain_longueur_m: float = Field(..., description="Longueur en mètres")

    # Métriques (utiles pour la comparaison de projets)
    nb_objets_total: int = Field(..., description="Nombre total d'objets")
    surface_occupee_pct: float = Field(
        ..., ge=0, le=100,
        description="% de la surface occupée"
    )
    conforme_normes: bool = Field(
        ...,
        description="True si toutes les contraintes sont respectées"
    )
    avertissements: list[str] = Field(
        default=[],
        description="Messages d'avertissement non bloquants"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "scene_id": "scene_abc123",
                "objets": [
                    {
                        "asset_id": "toboggan_001",
                        "nom": "Toboggan double lame",
                        "fichier_glb": "https://storage.example.com/toboggan_001.glb",
                        "position_x": 5.0,
                        "position_z": 8.0,
                        "position_y": 0.0,
                        "rotation_y": 45.0,
                        "scale": 1.0,
                        "categorie": "equipement"
                    }
                ],
                "terrain_largeur_m": 20.0,
                "terrain_longueur_m": 30.0,
                "nb_objets_total": 12,
                "surface_occupee_pct": 34.5,
                "conforme_normes": True,
                "avertissements": []
            }
        }