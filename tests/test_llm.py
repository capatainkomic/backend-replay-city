import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm_service import generer_liste_objets
import json

resultat = generer_liste_objets(
    project_type="aire_de_jeux",
    terrain_largeur_m=20.0,
    terrain_longueur_m=30.0,
    age_ranges=["3-6", "6-12"],
    accessibilite_pmr=False,
    description_libre="Theme foret avec beaucoup de vegetation"
)

# Affiche le JSON brut pour voir exactement ce que le LLM retourne
print("=== JSON BRUT DU LLM ===")
print(json.dumps(resultat, ensure_ascii=False, indent=2))