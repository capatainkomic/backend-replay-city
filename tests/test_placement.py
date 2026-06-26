import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.placement_service import placer_objets

# Simule ce que le LLM aurait retourné
objets_llm = [
    {
        "id_temp": "obj_1",
        "description_recherche": "structure de jeux avec toboggan",
        "categorie": "equipement",
        "priorite": "indispensable",
        "quantite": 1
    },
    {
        "id_temp": "obj_2",
        "description_recherche": "balancoire double",
        "categorie": "equipement",
        "priorite": "indispensable",
        "quantite": 1
    },
    {
        "id_temp": "obj_3",
        "description_recherche": "banc en bois pour parc",
        "categorie": "mobilier_urbain",
        "priorite": "indispensable",
        "quantite": 2
    },
    {
        "id_temp": "obj_4",
        "description_recherche": "arbre mature pour ombre",
        "categorie": "vegetation",
        "priorite": "recommande",
        "quantite": 3
    }
]

contraintes = [
    {"objet_1": "obj_1", "relation": "centre", "objet_2": "centre"},
    {"objet_1": "obj_2", "relation": "loin_de", "objet_2": "obj_1"},
    {"objet_1": "obj_3", "relation": "borde", "objet_2": "perimetre"},
    {"objet_1": "obj_4", "relation": "borde", "objet_2": "perimetre"},
]

objets_places, avertissements = placer_objets(
    objets_llm=objets_llm,
    contraintes=contraintes,
    terrain_largeur_m=20.0,
    terrain_longueur_m=30.0,
    accessibilite_pmr=False
)

print(f"Objets places : {len(objets_places)}")
print()
for obj in objets_places:
    type_label = "PLACEHOLDER" if obj.type == "placeholder" else "ASSET"
    print(f"[{type_label}] {obj.nom}")
    print(f"  position : x={obj.position_x:.1f}m  z={obj.position_z:.1f}m")
    print(f"  rotation : {obj.rotation_y}deg")
    print(f"  taille   : {obj.largeur_m}m x {obj.longueur_m}m x {obj.hauteur_m}m")
    if obj.similarite:
        print(f"  similarite : {round(obj.similarite, 3)}")
    print()

if avertissements:
    print("Avertissements :")
    for a in avertissements:
        print(f"  -> {a}")