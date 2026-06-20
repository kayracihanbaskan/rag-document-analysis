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

    # --- Embedding (lokal BGE-M3) ---
    bge_model_name: str = "BAAI/bge-m3"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
