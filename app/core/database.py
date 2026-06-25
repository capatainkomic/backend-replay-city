"""
CONNEXION BASE DE DONNÉES
"""

from supabase import create_client, Client
from app.core.config import settings


def get_supabase_client() -> Client:
    """
    Crée et retourne un client Supabase.
    Utilisé pour lire/écrire dans les tables.
    """
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )



supabase = get_supabase_client()