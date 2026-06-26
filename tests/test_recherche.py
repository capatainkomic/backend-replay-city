import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.library_service import rechercher_assets

# Test 1 : recherche d'un équipement de grimpe
resultats = rechercher_assets("equipement de grimpe pour enfants", limite=2)
print("Test 1 - grimpe :")
for r in resultats:
    print(f"  -> {r['nom']} (similarite: {round(r['similarite'], 3)})")

print()

# Test 2 : recherche de vegetation pour l'ombre
resultats2 = rechercher_assets("arbre pour donner de l ombre", categorie="vegetation", limite=2)
print("Test 2 - ombre :")
for r in resultats2:
    print(f"  -> {r['nom']} (similarite: {round(r['similarite'], 3)})")