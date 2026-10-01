"""
config/settings.py
Central application configuration loaded from .env
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ─────────────────────────────────────────────────────────────
    # App
    # ─────────────────────────────────────────────────────────────
    app_name: str = "ResumeAI"
    app_env: str = "development"
    log_level: str = "DEBUG"

    # ─────────────────────────────────────────────────────────────
    # Ollama / LLM
    # ─────────────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    ollama_temperature: float = 0.1
    ollama_num_predict: int = 800
    ollama_num_ctx: int = 2048
    ollama_embedding_model: str = "nomic-embed-text"

    # ─────────────────────────────────────────────────────────────
    # ChromaDB / Vector Store
    # ─────────────────────────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_resume_collection: str = "resumes"
    chroma_jd_collection: str = "job_descriptions"

    # ─────────────────────────────────────────────────────────────
    # PostgreSQL
    # ─────────────────────────────────────────────────────────────
    postgres_user: str = "postgres"
    postgres_password: str = "Tushar@21"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "resume_ai"

    # ─────────────────────────────────────────────────────────────
    # Authentication / JWT
    # ─────────────────────────────────────────────────────────────
    jwt_secret_key: str ="3Hn6aytVUIdn5tiF6Dq8GLMmJIkC0bIYiCTUZo34YK0"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # ─────────────────────────────────────────────────────────────
    # API
    # ─────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # ─────────────────────────────────────────────────────────────
    # Agents
    # ─────────────────────────────────────────────────────────────
    agent_max_retries: int = 3
    agent_timeout_seconds: int = 300
    screener_top_k: int = 20
    recommender_top_k: int = 10

    # ─────────────────────────────────────────────────────────────
    # Environment file
    # ─────────────────────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    """
    return Settings()