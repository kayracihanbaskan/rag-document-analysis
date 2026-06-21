from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env dosyasini otomatik okur; ortam degiskenleri onceliklidir.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM (OpenRouter uzerinden) ---
    openrouter_api_key: str = Field(...)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openai/gpt-4o-mini"

    # --- Embedding (lokal BGE-small) ---
    bge_model_name: str = "BAAI/bge-small-en-v1.5"
    bge_device: str = "cpu"
    bge_max_length: int = 512
    bge_batch_size: int = 16

    # --- Vector store ---
    chroma_persist_dir: Path = Path("./data/chroma")
    chroma_collection: str = "documents"

    # --- Chunking ---
    chunk_size: int = 800
    chunk_overlap: int = 120

    # --- Upload ---
    upload_dir: Path = Path("./data/uploads")
    max_upload_mb: int = 20

    # --- Celery / Redis (async ingestion queue) ---
    celery_broker_url: str = "redis://127.0.0.1:6379/0"
    celery_result_backend: str = "redis://127.0.0.1:6379/1"
    # Task sonuclarini ne kadar tutalim (1 saat); sonra Redis otomatik temizler
    celery_result_expires_seconds: int = 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
