"""
Ingestion tasklari (Celery worker'da calisir).

Neden senkron IngestionService'i task icinde kullanabiliyoruz?
- BGE ve Chroma zaten senkron API; task zaten kendi thread'inde calisiyor
- self.update_state ile progress yayinlanir (Frontend polling icin)
"""
from pathlib import Path

from celery import shared_task

from app.celery_app import celery_app
from app.core.config import get_settings
from app.services.embedder import BGEEmbedder
from app.services.ingestion import IngestionService
from app.services.vector_store import VectorStore


def _make_service() -> IngestionService:
    """Worker process'inde model/DB instance'lari olustur (her task icin degil, lazy)."""
    settings = get_settings()
    embedder = BGEEmbedder(settings)
    vector_store = VectorStore(settings)
    return IngestionService(settings, embedder, vector_store)


@celery_app.task(
    bind=True,
    name="app.tasks.ingestion.ingest_pdf",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def ingest_pdf(self, document_id: str, filename: str, pdf_path_str: str) -> dict:
    """
    PDF'i parse et, chunk'la, embed'le, Chroma'ya yaz.
    UI'a ilerleme bildirmek icin self.update_state kullanir.
    """
    self.update_state(state="PROGRESS", meta={"stage": "basladi", "percent": 0})
    pdf_path = Path(pdf_path_str)
    service = _make_service()

    # IngestionService.ingest() tek seferlik pipeline; ilerleme sema ekleyebiliriz
    # ama simdilik 2 asamali bildirim yeterli: PROGRESS + SUCCESS
    self.update_state(state="PROGRESS", meta={"stage": "parse + chunk + embed", "percent": 30})

    result = service.ingest(document_id, filename, pdf_path)

    self.update_state(state="PROGRESS", meta={"stage": "chroma'ya yazildi", "percent": 95})
    return result
