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
    accessibilite_pmr: bool,
    description_libre: str = None
) -> dict:
    """
    Demande au LLM de générer la liste des objets nécessaires
    et leurs contraintes spatiales pour le projet.
    """
    prompt = _construire_prompt(
        project_type,
        terrain_largeur_m,
        terrain_longueur_m,
        age_ranges,
        accessibilite_pmr,
        description_libre
    )

    try:
        response = client.chat.complete(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        texte = response.choices[0].message.content
        return _extraire_json(texte)

    except Exception as e:
        print(f"❌ Erreur LLM : {e}")
        return _resultat_defaut(project_type)


def _construire_prompt(
    project_type: str,
    terrain_largeur_m: float,
    terrain_longueur_m: float,
    age_ranges: list[str],
    accessibilite_pmr: bool,
    description_libre: str = None
) -> str:

    types_projets = {
        "aire_de_jeux": "aire de jeux extérieure",
        "jardin_pedagogique": "jardin pédagogique",
        "espace_lecture": "espace lecture extérieur",
        "espace_sportif": "espace sportif"
    }

    ages_texte = ", ".join(age_ranges)
    pmr_texte = "Le projet DOIT être accessible aux personnes à mobilité réduite (PMR)." if accessibilite_pmr else ""
    description_texte = f"Description spécifique du client : {description_libre}" if description_libre else ""
    surface = terrain_largeur_m * terrain_longueur_m

    prompt = f"""Tu es un expert en aménagement d'espaces extérieurs pour enfants.

Tu dois planifier une {types_projets.get(project_type, project_type)} pour un terrain de {terrain_largeur_m}m x {terrain_longueur_m}m ({surface}m²).
Tranches d'age ciblees : {ages_texte}
{pmr_texte}
{description_texte}

Genere une liste d'objets et leur organisation spatiale pour ce projet.

REGLES IMPORTANTES :
- Adapte le nombre d'objets a la taille du terrain (terrain petit = moins d'objets)
- Ne propose que des objets realistes pour ce type d'espace
- Pense a la securite et a la circulation entre les objets
- Inclus toujours quelques elements de vegetation
- Inclus toujours quelques elements de mobilier urbain (bancs, poubelles)

Reponds UNIQUEMENT avec un JSON valide, sans texte avant ou apres, sans balises markdown, dans ce format exact :

{{
  "objets": [
    {{
      "id_temp": "obj_1",
      "description_recherche": "description courte pour trouver l'objet dans la bibliotheque",
      "categorie": "equipement | vegetation | mobilier_urbain",
      "priorite": "indispensable | recommande | bonus",
      "quantite": 1
    }}
  ],
  "zones": [
    {{
      "nom": "nom de la zone",
      "description": "description de la zone",
      "pourcentage_terrain": 30
    }}
  ],
  "contraintes": [
    {{
      "objet_1": "id_temp de l'objet 1",
      "relation": "loin_de | proche_de | borde | centre",
      "objet_2": "id_temp de l'objet 2 OU entree OU perimetre OU centre"
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