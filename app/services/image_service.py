"""
SERVICE GÉNÉRATION 2D — app/services/image_service.py
Utilise DALL-E 3 pour générer une image 2D (plan de masse).
"""

import base64
from openai import OpenAI
from app.core.config import settings
from app.core.database import supabase
import uuid

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def generer_image_2d(
    project_type: str,
    terrain_largeur_m: float,
    terrain_longueur_m: float,
    age_ranges: list[str],
    budget_euros: float = None
) -> str | None:

    prompt = _construire_prompt_image(
        project_type,
        terrain_largeur_m,
        terrain_longueur_m,
        age_ranges,
        budget_euros
    )

    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
            n=1
        )

        image_base64 = response.data[0].b64_json
        if not image_base64:
            return None

        # Décode le base64 en bytes
        image_bytes = base64.b64decode(image_base64)

        # Sauvegarde dans Supabase Storage
        nom_fichier = f"plans-2d/{uuid.uuid4()}.png"
        supabase.storage.from_("assets-3d").upload(
            path=nom_fichier,
            file=image_bytes,
            file_options={"content-type": "image/png"}
        )

        # Récupère l'URL publique
        url = supabase.storage.from_("assets-3d").get_public_url(nom_fichier)
        print(f"✅ Image 2D sauvegardée : {url}")
        return url

    except Exception as e:
        print(f"❌ Erreur génération image : {e}")
        return None

def _construire_prompt_image(
    project_type: str,
    terrain_largeur_m: float,
    terrain_longueur_m: float,
    age_ranges: list[str],
    budget_euros: float = None
) -> str:

    types_projets = {
        "aire_de_jeux":       "children's playground",
        "jardin_pedagogique": "educational garden for children",
        "espace_lecture":     "outdoor reading space for children",
        "espace_sportif":     "outdoor sports area for children"
    }

    ages_texte = ", ".join(age_ranges)
    surface = terrain_largeur_m * terrain_longueur_m

    if budget_euros and budget_euros < 5000:
        budget_texte = "simple and modest equipment, basic playground"
    elif budget_euros and budget_euros < 20000:
        budget_texte = "standard equipment, well-equipped playground"
    elif budget_euros and budget_euros >= 20000:
        budget_texte = "premium equipment, rich and diverse playground"
    else:
        budget_texte = ""

    prompt = f"""Photorealistic aerial view illustration of a {types_projets.get(project_type, "children's outdoor space")}, seen from above at a slight angle (isometric view).

Terrain size: {terrain_largeur_m}m x {terrain_longueur_m}m.
Target age: {ages_texte} years old.
{budget_texte}

The scene should show:
- Colorful modern play equipment (slides, swings, climbing structures) on a sand surface
- Wooden benches and picnic tables on grass areas
- Trees and bushes around the perimeter
- A wooden fence surrounding the space
- Natural grass ground, with a sandy play area in the center
- Paved pathways connecting different zones

Style: realistic 3D render, bright daylight, soft shadows, 
vibrant colors, professional landscape architecture visualization,
photorealistic materials (wood, metal, sand, grass).
NOT a flat 2D plan, NOT a cartoon, NOT a diagram.
This should look like a real photograph taken from a drone."""

    return prompt

def analyser_image_equipements(
    url_image: str,
    budget_euros: float = None
) -> dict:
    """
    Utilise GPT-4o vision pour analyser l'image générée
    et extraire la liste des équipements visibles avec estimation de coût.
    """
    try:
        budget_texte = f"Le budget total est de {budget_euros}€." if budget_euros else ""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": url_image}
                        },
                        {
                            "type": "text",
                            "text": f"""Analyse cette image d'une aire de jeux et liste TOUS les éléments visibles sans exception.
{budget_texte}

Liste absolument tout ce qui est visible :
- Tous les équipements de jeux
- Tout le mobilier urbain (bancs, tables de pique-nique, poubelles)
- Toute la végétation (arbres, arbustes)
- Les aménagements (clôture, allées, sol amortissant)

Pour chaque élément visible, donne :
- Le nom précis en français
- La quantité exacte visible
- Le coût unitaire estimé en euros (prix marché français collectivités)

Calcule le coût total en additionnant quantite x cout_unitaire pour chaque élément.
Estime le pourcentage de surface occupée par les équipements.

Réponds UNIQUEMENT avec un JSON valide sans texte ni balises markdown :

{{
  "equipements": [
    {{
      "nom": "Toboggan double lame",
      "quantite": 2,
      "cout_unitaire": 1500
    }}
  ],
  "surface_occupee_pct": 65,
  "cout_total_euros": 15000
}}"""
                        }
                    ]
                }
            ],
            max_tokens=1000
        )

        texte = response.choices[0].message.content
        # Réutilise _extraire_json de llm_service
        import json
        import re
        try:
            return json.loads(texte)
        except:
            texte_nettoye = re.sub(r"```json\s*", "", texte)
            texte_nettoye = re.sub(r"```\s*", "", texte_nettoye).strip()
            return json.loads(texte_nettoye)

    except Exception as e:
        print(f"❌ Erreur analyse image : {e}")
        return {
            "equipements": [],
            "surface_occupee_pct": 70.0,
            "cout_total_euros": budget_euros or 10000
        }