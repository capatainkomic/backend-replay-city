"""
SERVICE LLM — app/services/llm_service.py
Utilise Mistral AI (gratuit) pour générer la liste des objets
et leurs contraintes spatiales depuis le formulaire utilisateur.
"""

from mistralai import Mistral
from app.core.config import settings
import json
import re

# Initialisation du client Mistral
client = Mistral(api_key=settings.MISTRAL_API_KEY)
MODEL = "mistral-small-latest"


def generer_liste_objets(
    project_type: str,
    terrain_largeur_m: float,
    terrain_longueur_m: float,
    age_ranges: list[str],
    budget_euros: float = None
) -> dict:

    prompt = _construire_prompt(
        project_type,
        terrain_largeur_m,
        terrain_longueur_m,
        age_ranges,
        budget_euros
    )

    try:
        response = client.chat.complete(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        texte = response.choices[0].message.content
        resultat = _extraire_json(texte)

        zones_validees = _valider_zones(
            resultat.get("zones", []),
            terrain_largeur_m,
            terrain_longueur_m
        )
        resultat["zones"] = zones_validees

        objets_plats = []
        for zone in resultat.get("zones", []):
            for obj in zone.get("objets", []):
                obj["zone_id"] = zone["id"]
                obj["zone_x_debut"] = zone["x_debut"]
                obj["zone_z_debut"] = zone["z_debut"]
                obj["zone_largeur"] = zone["largeur"]
                obj["zone_longueur"] = zone["longueur"]
                objets_plats.append(obj)

        return {
            "objets": objets_plats,
            "zones": resultat.get("zones", []),
            "contraintes": resultat.get("contraintes", [])
        }

    except Exception as e:
        print(f"Erreur LLM : {e}")
        return _resultat_defaut(project_type)


def _construire_prompt(
    project_type: str,
    terrain_largeur_m: float,
    terrain_longueur_m: float,
    age_ranges: list[str],
    budget_euros: float = None
) -> str:

    types_projets = {
        "aire_de_jeux": "aire de jeux extérieure",
        "jardin_pedagogique": "jardin pédagogique",
        "espace_lecture": "espace lecture extérieur",
        "espace_sportif": "espace sportif"
    }

    ages_texte = ", ".join(age_ranges)
    surface = terrain_largeur_m * terrain_longueur_m

    if budget_euros and budget_euros < 5000:
        budget_texte = f"Budget limité : {budget_euros}€ — équipements simples et peu nombreux"
    elif budget_euros and budget_euros < 20000:
        budget_texte = f"Budget moyen : {budget_euros}€ — équipements standards"
    elif budget_euros and budget_euros >= 20000:
        budget_texte = f"Budget confortable : {budget_euros}€ — équipements variés et de qualité"
    else:
        budget_texte = ""

    prompt = f"""Tu es un expert en aménagement d'espaces extérieurs pour enfants.

    TERRAIN : {terrain_largeur_m}m (largeur, axe X) x {terrain_longueur_m}m (longueur, axe Z) = {surface}m²
    Origine (0,0) = coin bas-gauche du terrain.
    Axe X = gauche vers droite. Axe Z = bas vers haut.
    {budget_texte}

    PROJET : {types_projets.get(project_type, project_type)}
    TRANCHES D'AGE : {ages_texte}

    ETAPE 1 — Découpe le terrain en zones fonctionnelles.
    Chaque zone est un rectangle défini par :
    - x_debut, z_debut : coin bas-gauche de la zone (en mètres depuis l'origine)
    - largeur (axe X), longueur (axe Z) : dimensions de la zone

    Règles impératives :
    - Les zones ne doivent PAS se chevaucher
    - Les zones doivent couvrir la majorité du terrain
    - Laisse une marge de 1m sur chaque bord du terrain
    - Prévoir toujours : 1 zone centrale pour équipements principaux, 1 zone végétation en bordure, 1 zone repos/mobilier

    ETAPE 2 — Pour chaque zone, liste les objets à y placer.
    Adapte le nombre d'objets à la SURFACE RÉELLE de la zone.
    Règle : max 1 objet par 4m² de zone.

    Reponds UNIQUEMENT avec un JSON valide, sans texte avant ou apres, sans balises markdown :

    {{
    "zones": [
        {{
        "id": "zone_1",
        "nom": "nom court de la zone",
        "type": "jeux_actifs | repos | vegetation | entree | mixte",
        "x_debut": 1.0,
        "z_debut": 1.0,
        "largeur": 8.0,
        "longueur": 10.0,
        "objets": [
            {{
            "id_temp": "obj_1",
            "description_recherche": "description courte pour trouver l'objet",
            "categorie": "equipement | vegetation | mobilier_urbain",
            "priorite": "indispensable | recommande | bonus",
            "quantite": 1
            }}
        ]
        }}
    ],
    "contraintes": [
        {{
        "objet_1": "obj_1",
        "relation": "loin_de | proche_de | face_a | borde",
        "objet_2": "obj_2"
        }}
    ]
    }}"""

    return prompt


def _extraire_json(texte: str) -> dict:
    """
    Extrait le JSON depuis la réponse du LLM.
    Nettoie les balises markdown si présentes.
    """
    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        pass

    texte_nettoye = re.sub(r"```json\s*", "", texte)
    texte_nettoye = re.sub(r"```\s*", "", texte_nettoye)
    texte_nettoye = texte_nettoye.strip()

    try:
        return json.loads(texte_nettoye)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{.*\}', texte, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    print(f"Impossible d'extraire le JSON — reponse brute : {texte[:200]}")
    return _resultat_defaut("inconnu")


def _resultat_defaut(project_type: str) -> dict:
    """
    Retourne un résultat minimal si le LLM échoue.
    """
    return {
        "objets": [
            {
                "id_temp": "obj_1",
                "description_recherche": "banc extérieur pour parc",
                "categorie": "mobilier_urbain",
                "priorite": "indispensable",
                "quantite": 2
            },
            {
                "id_temp": "obj_2",
                "description_recherche": "arbre pour espace vert",
                "categorie": "vegetation",
                "priorite": "recommande",
                "quantite": 3
            }
        ],
        "zones": [],
        "contraintes": []
    }

def _valider_zones(zones: list, terrain_largeur_m: float, terrain_longueur_m: float) -> list:
    """
    Corrige les zones qui dépassent les limites du terrain.
    """
    zones_corrigees = []
    for zone in zones:
        x_debut = max(1.0, min(zone["x_debut"], terrain_largeur_m - 2))
        z_debut = max(1.0, min(zone["z_debut"], terrain_longueur_m - 2))
        largeur = min(zone["largeur"], terrain_largeur_m - x_debut - 1)
        longueur = min(zone["longueur"], terrain_longueur_m - z_debut - 1)

        if largeur < 1.0 or longueur < 1.0:
            print(f"Zone '{zone['id']}' ignorée — trop petite après correction")
            continue

        zone_corrigee = {**zone, "x_debut": x_debut, "z_debut": z_debut,
                        "largeur": largeur, "longueur": longueur}
        zones_corrigees.append(zone_corrigee)

    return zones_corrigees

def generer_metriques_2d(
    project_type: str,
    terrain_largeur_m: float,
    terrain_longueur_m: float,
    age_ranges: list[str],
    budget_euros: float = None
) -> dict:
    """
    Génère les métriques du projet pour la réponse 2D :
    liste des équipements, coût estimé, surface utilisée.
    """
    surface = terrain_largeur_m * terrain_longueur_m

    types_projets = {
        "aire_de_jeux": "aire de jeux extérieure",
        "jardin_pedagogique": "jardin pédagogique",
        "espace_lecture": "espace lecture extérieur",
        "espace_sportif": "espace sportif"
    }

    ages_texte = ", ".join(age_ranges)

    if budget_euros:
        budget_texte = f"Budget disponible : {budget_euros}€"
    else:
        budget_texte = "Pas de budget défini, propose un budget raisonnable"

    prompt = f"""Tu es un expert en aménagement d'espaces extérieurs pour enfants.

Projet : {types_projets.get(project_type, project_type)}
Terrain : {terrain_largeur_m}m x {terrain_longueur_m}m ({surface}m²)
Tranches d'âge : {ages_texte}
{budget_texte}

Génère une liste réaliste des équipements pour ce projet avec :
- Le nom de chaque équipement
- La quantité
- Le coût unitaire estimé en euros (prix marché français)

Reponds UNIQUEMENT avec un JSON valide sans texte ni balises markdown :

{{
  "equipements": [
    {{
      "nom": "Toboggan double lame",
      "quantite": 1,
      "cout_unitaire": 1500
    }}
  ],
  "surface_occupee_pct": 75,
  "cout_total_euros": 15000
}}"""

    try:
        response = client.chat.complete(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        texte = response.choices[0].message.content
        return _extraire_json(texte)

    except Exception as e:
        print(f"Erreur LLM métriques : {e}")
        return {
            "equipements": [],
            "surface_occupee_pct": 70.0,
            "cout_total_euros": budget_euros or 10000
        }