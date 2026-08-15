"""
config/settings.py
──────────────────
Central config — loaded once at startup from .env file.
All agents and services import from here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ───────────────────────────────────────────────────────
    app_name: str = "ResumeAI"
    app_env: str = "development"
    log_level: str = "DEBUG"

    # ── Ollama ────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "phi3:mini"
    ollama_temperature: float = 0.1
    ollama_num_predict: int = 800
    ollama_num_ctx: int = 2048
    ollama_embedding_model: str = "nomic-embed-text"

    # ── ChromaDB ──────────────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_resume_collection: str = "resumes"
    chroma_jd_collection: str = "job_descriptions"

    # ── API ───────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # ── Agents ────────────────────────────────────────────────────
    agent_max_retries: int = 3
    agent_timeout_seconds: int = 300
    screener_top_k: int = 20
    recommender_top_k: int = 10


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached singleton Settings instance."""
    return Settings()