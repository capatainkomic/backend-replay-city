from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Toutes les variables de configuration du projet.
    Pydantic lit automatiquement les valeurs depuis le fichier .env
    """

    # Infos générales
    APP_NAME: str = "RePlay City API"
    APP_ENV: str = "development"

    # LLM
    GEMINI_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Base de données
    DATABASE_URL: str = ""

    # Supabase 
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""


    # Stockage fichiers 3D
    STORAGE_URL: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """
    Retourne les settings en cache.
    lru_cache = le fichier .env est lu une seule fois,
    pas à chaque requête
    """
    return Settings()


# On crée un objet global 'settings' importable partout
settings = get_settings()