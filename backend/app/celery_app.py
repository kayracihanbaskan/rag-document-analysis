"""
Celery uygulamasi: ingestion tasklari arka planda calissin.

Mimari:
- API (uvicorn) task uretir, sonuc beklemeden 202 + task_id doner
- Worker (ayri process) kuyruktan task alir, BGE + Chroma ile yapar
- Sonuc Redis'te saklanir; /jobs/{id} endpoint'i ile sorgulanir
"""
from celery import Celery
from celery.utils.log import get_task_logger

from app.core.config import get_settings

logger = get_task_logger(__name__)

settings = get_settings()

# Celery app: broker (mesaj kuyrugu) + result backend (sonuc saklama)
# task_track_started=True: started state'i de takip edilir, frontend "isleniyor" gosterir
celery_app = Celery(
    "rag",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.ingestion"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    # Sonuclar 1 saat sonra otomatik temizlensin
    result_expires=settings.celery_result_expires_seconds,
    # Tek worker tek task (CPU-bound is; paralellesirse RAM patlar)
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    timezone="UTC",
)

# Eager mode: Redis olmadan task senkron calissin (test/dev).
# Production'da CALISMAZ; sadece uvicorn + worker ayri process.
# Aktiflemek icin: CELERY_EAGER=true env degiskeni.
import os

if os.getenv("CELERY_EAGER", "").lower() in ("1", "true", "yes"):
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )
