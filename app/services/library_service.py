"""
Ce service gère la recherche sémantique dans la bibliothèque d'assets.

Fonctionnement :
1. Prend une description textuelle en entrée
   ex: "toboggan coloré pour enfants de 3 à 6 ans"
2. Calcule l'embedding de cette description
3. Compare avec tous les embeddings de la bibliothèque via pgvector
4. Retourne les N assets les plus proches sémantiquement
"""

from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.core.database import supabase
import json


print("Chargement du modèle d'embedding...")
model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
print("✅ Modèle d'embedding chargé")


def rechercher_assets(
    description: str,
    categorie: str = None,
    limite: int = 3
) -> list[dict]:
    """
    Recherche les assets les plus proches d'une description.

    Args:
        description : texte décrivant le besoin
                      ex: "équipement de grimpe pour enfants"
        categorie   : filtre optionnel par catégorie
                      ex: "equipement", "vegetation", "mobilier_urbain"
        limite      : nombre maximum de résultats à retourner

    Returns:
        Liste de dicts contenant les assets trouvés avec leur score
    """

    # 1. Calcul de l'embedding de la description recherchée
    embedding = model.encode(description).tolist()

    # 2. Recherche par similarité cosinus dans Supabase via pgvector
    # On utilise une fonction RPC (Remote Procedure Call) qu'on va
    # créer dans Supabase pour faire la recherche vectorielle
    try:
        result = supabase.rpc(
            "rechercher_assets_similaires",
            {
                "query_embedding": embedding,
                "categorie_filtre": categorie,
                "limite": limite
            }
        ).execute()

        return result.data

    except Exception as e:
        print(f"❌ Erreur recherche sémantique : {e}")
        return []


def get_asset_par_id(asset_id: str) -> dict | None:
    """
    Récupère un asset par son ID.
    Utilisé pour vérifier si un asset existe avant de le générer.
    """
    try:
        result = supabase.table("assets")\
            .select("*")\
            .eq("id", asset_id)\
            .single()\
            .execute()
        return result.data
    except Exception as e:
        print(f"❌ Erreur récupération asset : {e}")
        return None


def sauvegarder_asset(asset_data: dict) -> dict | None:
    """
    Sauvegarde un nouvel asset dans la bibliothèque.
    Utilisé quand un objet manquant est généré par Meshy/Tripo.
    """
    try:
        # Calcul de l'embedding depuis nom + description
        texte = f"{asset_data['nom']}. {asset_data['description']}"
        embedding = model.encode(texte).tolist()
        asset_data["embedding"] = embedding

        result = supabase.table("assets")\
            .insert(asset_data)\
            .execute()

        print(f"✅ Nouvel asset sauvegardé : {asset_data['nom']}")
        return result.data[0]

    except Exception as e:
        print(f"❌ Erreur sauvegarde asset : {e}")
        return None