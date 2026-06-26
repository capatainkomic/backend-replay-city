"""
SCRIPT D'INSERTION DES ASSETS — scripts/insert_assets.py

Ce script fait 3 choses automatiquement :
1. Lit chaque fichier GLB et calcule sa bounding box brute
2. Calcule le scale pour ramener le modèle à sa taille réelle
3. Insère toutes les données dans Supabase
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import trimesh
from app.core.config import settings
from supabase import create_client

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# ─────────────────────────────────────────────
# DONNÉES DES ASSETS
# taille_reelle = dimensions qu'on veut dans la scène (en mètres)
# ─────────────────────────────────────────────
ASSETS = [
    {
        "nom": "Toboggan ondulé avec escalier latéral",
        "description": "Toboggan grande lame ondulée en plastique bleu vif, monté sur une structure tubulaire métallique rouge avec escalier d'accès à marches beiges et rampes jaunes et grises. Équipement d'aire de jeux extérieure de taille moyenne à grande, destiné aux enfants de 4 à 10 ans, avec une lame sinueuse offrant une glisse dynamique. Structure robuste et colorée adaptée aux espaces de jeux collectifs.",
        "categorie": "equipement",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/equipement/toboggan_ondule.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\toboggan_ondule.glb",
        "taille_reelle": {"largeur": 1.5, "longueur": 3.0, "hauteur": 2.0},
        "accessible_pmr": False,
        "licence": "CC BY",
        "auteur": "vaedskalw",
        "source_url": "https://sketchfab.com/3d-models/slide-playground-e59c8559ba42463881732790dcbfbb3c"
    },
    {
        "nom": "Structure multi-jeux modulaire couverte avec toboggan et tunnel",
        "description": "Grande structure de jeux modulaire multi-activités composée de deux tours couvertes de toits inclinés jaunes et rouges, reliées par un pont à lattes rouges, avec un toboggan lame jaune, un tunnel cylindrique rouge, un ressort hélicoïdal rouge et une échelle d'accès inclinée verte. Équipement collectif extérieur destiné aux enfants de 3 à 10 ans.",
        "categorie": "equipement",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/equipement/structure_multijeux_couverte.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\structure_multijeux_couverte.glb",
        "taille_reelle": {"largeur": 4.0, "longueur": 7.0, "hauteur": 3.0},
        "accessible_pmr": False,
        "licence": "CC BY",
        "auteur": "OOtis_Pro",
        "source_url": "https://sketchfab.com/3d-models/swing-jhula-eaa20819643e42508a5a32383a9799dc"
    },
    {
        "nom": "Portique double balançoire biplace classique",
        "description": "Portique de balançoire double à structure tubulaire métallique jaune-vert et traverse horizontale bleue, équipé de deux sièges plats bleu marine suspendus par des chaînes métalliques. Équipement classique d'aire de jeux extérieure destiné aux enfants de 3 à 12 ans.",
        "categorie": "equipement",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/equipement/portique_balancoire_double.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\portique_balancoire_double.glb",
        "taille_reelle": {"largeur": 3.0, "longueur": 1.5, "hauteur": 2.5},
        "accessible_pmr": False,
        "licence": "CC BY",
        "auteur": "Glowbox 3D",
        "source_url": "https://sketchfab.com/3d-models/swing-set-8712f53da0e04736802f1bc84ca7df97"
    },
    {
        "nom": "Structure multi-jeux premium",
        "description": "Grande structure de jeux modulaire haute gamme composée de tours hexagonales à toits pointus bleu marine, reliées par des filets de grimpe rouges et des passerelles, intégrant un toboggan hélicoïdal et un mur d'escalade. Équipement collectif extérieur de grande envergure destiné aux enfants de 4 à 12 ans.",
        "categorie": "equipement",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/equipement/structure_multijeux_premium.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\structure_multijeux_premium.glb",
        "taille_reelle": {"largeur": 8.0, "longueur": 12.0, "hauteur": 4.0},
        "accessible_pmr": False,
        "licence": "CC BY",
        "auteur": "99.Miles",
        "source_url": "https://sketchfab.com/3d-models/low-poly-kids-playground-61c6f6f70db14bbb89ecdfa04b99bbc6"
    },
    {
        "nom": "Tourniquet plateforme circulaire multicolore",
        "description": "Tourniquet de grande taille à plateforme circulaire en plastique multicolore, composé d'une rampe spiralée en colimaçon autour d'un axe central bleu avec volant de commande. Équipement de rotation collectif destiné aux enfants de 4 à 12 ans.",
        "categorie": "equipement",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/equipement/tourniquet_plateforme.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\tourniquet_plateforme.glb",
        "taille_reelle": {"largeur": 3.5, "longueur": 3.5, "hauteur": 1.5},
        "accessible_pmr": False,
        "licence": "CC BY",
        "auteur": "saqib24",
        "source_url": "https://sketchfab.com/3d-models/merry-go-round-9f66d13ad43646919086bc5a161f0f70"
    },
    {
        "nom": "Portique de grimpe double échelle",
        "description": "Structure de grimpe tubulaire métallique rouge et jaune composée de deux cadres en A reliés par des barreaux horizontaux jaunes formant une double échelle inclinée. Équipement classique d'aire de jeux destiné aux enfants de 5 à 12 ans.",
        "categorie": "equipement",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/equipement/portique_grimpe_double.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\portique_grimpe_double.glb",
        "taille_reelle": {"largeur": 3.0, "longueur": 1.5, "hauteur": 2.0},
        "accessible_pmr": False,
        "licence": "CC BY",
        "auteur": "mira9",
        "source_url": "https://sketchfab.com/3d-models/children-climbing-frame-red-yellow-1e6122eb887d4966a7e26a1dee4dec63"
    },
    {
        "nom": "Balançoire à bascule biplace classique",
        "description": "Bascule de jeux biplace en planche plate beige clair sur pivot central orange vif, équipée de deux paires de poignées en V orange. Équipement classique d'aire de jeux destiné aux enfants de 3 à 10 ans, favorisant le jeu coopératif.",
        "categorie": "equipement",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/equipement/bascule_biplace.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\bascule_biplace.glb",
        "taille_reelle": {"largeur": 2.0, "longueur": 0.5, "hauteur": 1.0},
        "accessible_pmr": False,
        "licence": "CC BY",
        "auteur": "Adeel",
        "source_url": "https://sketchfab.com/3d-models/low-poly-seesaw-f933c1b6b46e479697e043bc06c570a6"
    },
    {
        "nom": "Banc public classique bois et fonte",
        "description": "Banc extérieur traditionnel à lattes de bois massif teinte brun-rouge chaud, monté sur des pieds en fonte gris anthracite. Mobilier urbain classique destiné aux espaces de repos dans les aires de jeux et parcs.",
        "categorie": "mobilier_urbain",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/mobilier_urbain/banc_classique.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\banc_classique.glb",
        "taille_reelle": {"largeur": 1.8, "longueur": 0.6, "hauteur": 0.9},
        "accessible_pmr": True,
        "licence": "CC BY",
        "auteur": "Berk Gedik",
        "source_url": "https://sketchfab.com/3d-models/classic-park-bench-low-poly-01a5b64427984632bb44242da3813bb1"
    },
    {
        "nom": "Table de pique-nique bois naturel avec bancs intégrés",
        "description": "Table de pique-nique en bois naturel clair à lattes apparentes, structure monobloc avec deux bancs latéraux intégrés fixés par des pieds en X croisés. Mobilier extérieur polyvalent destiné aux espaces de repos dans les aires de jeux.",
        "categorie": "mobilier_urbain",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/mobilier_urbain/table_pique_nique.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\table_pique_nique.glb",
        "taille_reelle": {"largeur": 1.5, "longueur": 1.2, "hauteur": 0.75},
        "accessible_pmr": True,
        "licence": "CC BY",
        "auteur": "MaX3Dd",
        "source_url": "https://sketchfab.com/3d-models/picnic-table-low-poly-0781d9085e764583bc0a61f26cd4d01e"
    },
    {
        "nom": "Corbeille de propreté urbaine bois et métal à couvercle dôme",
        "description": "Corbeille extérieure cylindrique à lattes de bois naturel brun clair surmontée d'un couvercle dôme bombé en métal galvanisé argenté. Mobilier urbain de propreté destiné aux aires de jeux et espaces publics.",
        "categorie": "mobilier_urbain",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/mobilier_urbain/corbeille_bois_metal.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\corbeille_bois_metal.glb",
        "taille_reelle": {"largeur": 0.4, "longueur": 0.4, "hauteur": 0.9},
        "accessible_pmr": True,
        "licence": "CC BY",
        "auteur": "Kirill",
        "source_url": "https://sketchfab.com/3d-models/metal-trash-can-with-wooden-elements-c33157cdc92e4a8782cfe5a720ac547e"
    },
    {
        "nom": "Lampadaire double tête style classique en fonte",
        "description": "Lampadaire urbain à double bras symétriques de style classique en métal peint gris clair, avec deux abat-jours coniques orientés vers le bas. Mobilier d'éclairage extérieur destiné aux allées et périmètres d'aires de jeux.",
        "categorie": "mobilier_urbain",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/mobilier_urbain/lampadaire_double.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\lampadaire_double.glb",
        "taille_reelle": {"largeur": 0.4, "longueur": 0.4, "hauteur": 4.0},
        "accessible_pmr": True,
        "licence": "CC BY",
        "auteur": "Shahbaz Awan",
        "source_url": "https://sketchfab.com/3d-models/street-lamp-5c5afdd3410b460393957c270ab2f13a"
    },
    {
        "nom": "Arbre feuillu mature type chêne",
        "description": "Arbre 3D de grande taille à tronc épais brun texturé avec feuillage dense vert foncé évoquant un chêne méditerranéen mature. Élément végétal apportant ombre naturelle et intégration environnementale à la maquette.",
        "categorie": "vegetation",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/vegetation/arbre_chene.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\arbre_chene.glb",
        "taille_reelle": {"largeur": 6.0, "longueur": 6.0, "hauteur": 10.0},
        "accessible_pmr": True,
        "licence": "CC BY",
        "auteur": "massive-graphisme",
        "source_url": "https://sketchfab.com/3d-models/oak-tree-3dc59560f2d24345bdbe65c44636453b"
    },
    {
        "nom": "Arbre feuillu jeune adulte type tilleul ou peuplier",
        "description": "Arbre 3D de taille moyenne à tronc fin gris-brun avec feuillage vert vif évoquant un tilleul ou un peuplier. Élément végétal apportant légèreté visuelle sans obstruer les lignes de vue.",
        "categorie": "vegetation",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/vegetation/arbre_tilleul.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\arbre_tilleul.glb",
        "taille_reelle": {"largeur": 4.0, "longueur": 4.0, "hauteur": 7.0},
        "accessible_pmr": True,
        "licence": "CC BY",
        "auteur": "rhcreations",
        "source_url": "https://sketchfab.com/3d-models/small-ash-tree-5382ed9455b44e77ba3d2e128ce4b076"
    },
    {
        "nom": "Arbuste boule touffu vert vif",
        "description": "Arbuste 3D de forme sphérique compacte à feuillage dense vert vif évoquant un buis taillé en boule. Élément végétal destiné à la délimitation et l'habillage paysager des aires de jeux.",
        "categorie": "vegetation",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/vegetation/arbuste_boule.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\arbuste_boule.glb",
        "taille_reelle": {"largeur": 1.2, "longueur": 1.2, "hauteur": 1.0},
        "accessible_pmr": True,
        "licence": "CC BY",
        "auteur": "Natural_Disbuster",
        "source_url": "https://sketchfab.com/3d-models/cliff-shrub-for-terrain-7a0f2bf2982c4ff8bacc67856fdbfae2"
    },
    {
        "nom": "Touffe de fleurs jaunes type rudbeckie ou tournesol nain",
        "description": "Bouquet de fleurs 3D à pétales jaune vif et cœur brun foncé sur tiges vertes feuillues. Élément végétal décoratif destiné à l'embellissement des bordures et massifs des aires de jeux.",
        "categorie": "vegetation",
        "url_glb": "https://ghimnrtietnxcicxdoth.supabase.co/storage/v1/object/public/assets-3d/vegetation/fleurs_jaunes.glb",
        "fichier_local": r"C:\Users\magiq\Downloads\assets-3d\fleurs_jaunes.glb",
        "taille_reelle": {"largeur": 0.5, "longueur": 0.5, "hauteur": 0.6},
        "accessible_pmr": True,
        "licence": "CC BY",
        "auteur": "16874uy",
        "source_url": "https://sketchfab.com/3d-models/flower-99237f1d475244c9aed11c9979251ced"
    },
]


# ─────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────

def calculer_bounding_box_brute(fichier_glb: str) -> tuple:
    """
    Lit le fichier GLB et retourne les dimensions brutes
    telles qu'elles sont dans le fichier (sans conversion).
    """
    try:
        mesh = trimesh.load(fichier_glb)
        bounds = mesh.bounds
        largeur = abs(bounds[1][0] - bounds[0][0])
        hauteur = abs(bounds[1][1] - bounds[0][1])
        longueur = abs(bounds[1][2] - bounds[0][2])
        return largeur, hauteur, longueur
    except Exception as e:
        print(f"  ⚠️ Erreur lecture GLB : {e}")
        return None, None, None


def calculer_scale(brut_largeur, brut_longueur, brut_hauteur, taille_reelle):
    """
    Calcule le scale à appliquer pour passer des dimensions brutes
    aux dimensions réelles souhaitées.

    scale_x = largeur_reelle / largeur_brute
    scale_y = hauteur_reelle / hauteur_brute
    scale_z = longueur_reelle / longueur_brute
    """
    if not brut_largeur or brut_largeur == 0:
        return 1.0, 1.0, 1.0

    scale_x = round(taille_reelle["largeur"] / brut_largeur, 6)
    scale_y = round(taille_reelle["hauteur"] / brut_hauteur, 6)
    scale_z = round(taille_reelle["longueur"] / brut_longueur, 6)

    return scale_x, scale_y, scale_z


def calculer_rayon_securite(categorie: str, hauteur_m: float) -> float:
    """
    Calcule le rayon de sécurité indicatif selon la catégorie
    et la hauteur réelle de l'objet.
    """
    if categorie == "equipement":
        if hauteur_m <= 0.6:
            return 0.5
        elif hauteur_m <= 1.5:
            return 1.5
        else:
            return round((2/3) * hauteur_m + 0.5, 2)
    else:
        return 0.5


# ─────────────────────────────────────────────
# SCRIPT PRINCIPAL
# ─────────────────────────────────────────────

def main():
    print("🚀 Début de l'insertion des assets...\n")
    succes = 0
    erreurs = 0

    for asset in ASSETS:
        print(f"📦 Traitement : {asset['nom']}")

        # 1. Bounding box brute
        brut_l, brut_h, brut_lon = calculer_bounding_box_brute(asset["fichier_local"])

        if brut_l:
            print(f"   📐 Dimensions brutes : {round(brut_l,2)} × {round(brut_lon,2)} × {round(brut_h,2)}")
        else:
            brut_l, brut_h, brut_lon = 1.0, 1.0, 1.0

        # 2. Dimensions réelles souhaitées
        t = asset["taille_reelle"]
        print(f"   🎯 Taille réelle souhaitée : {t['largeur']}m × {t['longueur']}m × {t['hauteur']}m")

        # 3. Calcul du scale
        scale_x, scale_y, scale_z = calculer_scale(brut_l, brut_lon, brut_h, t)
        print(f"   ⚖️  Scale calculé : x={scale_x} y={scale_y} z={scale_z}")

        # 4. Rayon de sécurité basé sur la hauteur réelle
        rayon = calculer_rayon_securite(asset["categorie"], t["hauteur"])
        print(f"   🔒 Rayon de sécurité : {rayon}m")

        # 5. Insertion dans Supabase
        try:
            data = {
                "nom": asset["nom"],
                "description": asset["description"],
                "categorie": asset["categorie"],
                "url_glb": asset["url_glb"],
                "largeur_m": t["largeur"],
                "longueur_m": t["longueur"],
                "hauteur_m": t["hauteur"],
                "rayon_securite_m": rayon,
                "scale_x": scale_x,
                "scale_y": scale_y,
                "scale_z": scale_z,
                "accessible_pmr": asset["accessible_pmr"],
                "licence": asset["licence"],
                "auteur": asset["auteur"],
                "source_url": asset["source_url"],
            }

            result = supabase.table("assets").insert(data).execute()
            print(f"   ✅ Inséré — ID : {result.data[0]['id']}\n")
            succes += 1

        except Exception as e:
            print(f"   ❌ Erreur : {e}\n")
            erreurs += 1

    print(f"─────────────────────────────")
    print(f"✅ {succes} assets insérés")
    if erreurs > 0:
        print(f"❌ {erreurs} erreurs")


if __name__ == "__main__":
    main()