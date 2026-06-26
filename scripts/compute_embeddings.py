"""
Ce script :
1. Récupère tous les assets sans embedding depuis Supabase
2. Calcule l'embedding de chaque description avec sentence-transformers
3. Met à jour la table assets avec les embeddings calculés

Le modèle utilisé : paraphrase-multilingual-mpnet-base-v2
→ Choisi parce qu'il supporte le français nativement
→ Gratuit, tourne en local, pas besoin d'API
→ Produit des vecteurs de 768 dimensions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentence_transformers import SentenceTransformer
from app.core.config import settings
from supabase import create_client

# Connexion Supabase
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Chargement du modèle
# Le modèle sera téléchargé automatiquement la première fois (~400 Mo)
print("⏳ Chargement du modèle d'embedding...")
model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
print("✅ Modèle chargé\n")


def main():
    print(" Début du calcul des embeddings...\n")

    # 1. Récupère tous les assets sans embedding
    result = supabase.table("assets")\
        .select("id, nom, description")\
        .is_("embedding", "null")\
        .execute()

    assets = result.data
    print(f" {len(assets)} assets sans embedding trouvés\n")

    if not assets:
        print("✅ Tous les assets ont déjà un embedding !")
        return

    succes = 0
    erreurs = 0

    for asset in assets:
        print(f" Calcul embedding : {asset['nom']}")

        try:
            # 2. Calcule l'embedding depuis la description
            # On combine nom + description pour un embedding plus riche
            texte = f"{asset['nom']}. {asset['description']}"
            embedding = model.encode(texte)

            # Convertit le numpy array en liste Python
            # (nécessaire pour l'insertion JSON dans Supabase)
            embedding_list = embedding.tolist()

            # 3. Met à jour l'asset dans Supabase
            supabase.table("assets")\
                .update({"embedding": embedding_list})\
                .eq("id", asset["id"])\
                .execute()

            print(f"   ✅ Embedding calculé et sauvegardé\n")
            succes += 1

        except Exception as e:
            print(f"   ❌ Erreur : {e}\n")
            erreurs += 1

    print(f"─────────────────────────────")
    print(f"✅ {succes} embeddings calculés")
    if erreurs > 0:
        print(f"❌ {erreurs} erreurs")


if __name__ == "__main__":
    main()