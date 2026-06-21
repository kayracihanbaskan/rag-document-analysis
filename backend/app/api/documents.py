# HTTP katmani: 5 endpoint
# - POST /documents/upload        -> PDF yukle, ingestion task kuyruga at, 202 doner
# - GET  /jobs/{job_id}           -> Task ilerlemesini sorgula (polling)
# - GET  /documents/search        -> Metin sorgusu, top-K benzer chunk dondur
# - POST /documents/chat          -> Retrieval + LLM tam yanit (kaynak dahil)
# - POST /documents/chat/stream   -> Retrieval + LLM SSE (kaynak + token event'leri)

import json
import shutil
import uuid
from pathlib import Path

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.celery_app import celery_app
from app.core.config import Settings, get_settings
from app.schemas.documents import (
    ChatRequest,
    ChatResponse,
    ChatSource,
    IngestResponse,
    JobAccepted,
    JobStatus,
    SearchHit,
    SearchResponse,
)
from app.services.embedder import BGEEmbedder, get_embedder
from app.services.ingestion import IngestionService
from app.services.llm import OpenRouterLLM, get_llm
from app.services.rag import RagService
from app.services.vector_store import VectorStore

router = APIRouter(tags=["documents"])


# ---------- Dependency helpers ----------

def get_vector_store(settings: Settings = Depends(get_settings)) -> VectorStore:
    return VectorStore(settings)


def get_embedder_dep(settings: Settings = Depends(get_settings)) -> BGEEmbedder:
    return get_embedder(settings)


def get_llm_dep(settings: Settings = Depends(get_settings)) -> OpenRouterLLM:
    return get_llm(settings)


def get_rag_service(
    settings: Settings = Depends(get_settings),
    embedder: BGEEmbedder = Depends(get_embedder_dep),
    llm: OpenRouterLLM = Depends(get_llm_dep),
    vector_store: VectorStore = Depends(get_vector_store),
) -> RagService:
    return RagService(settings, embedder, llm, vector_store)


# ---------- Endpoints ----------

@router.post(
    "/documents/upload",
    response_model=JobAccepted,
    status_code=202,
)
async def upload_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> JobAccepted:
    """PDF'i kaydet, ingestion task'ini kuyruga at, hemen 202 dondur.

    Istemci status_url ile polling yaparak ilerlemeyi takip eder.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyalari kabul edilir.")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    document_id = str(uuid.uuid4())
    target = settings.upload_dir / f"{document_id}.pdf"

    try:
        with target.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    finally:
        await file.close()

    # Ingestion task'ini Celery kuyruguna at (worker arka planda calistiracak)
    from app.tasks.ingestion import ingest_pdf  # lazy import: worker baslamadan yuklenmesin

    async_result = ingest_pdf.delay(document_id, file.filename, str(target))
    job_id = async_result.id

    return JobAccepted(
        job_id=job_id,
        document_id=document_id,
        filename=file.filename,
        status_url=f"/jobs/{job_id}",
    )


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str) -> JobStatus:
    """Task ilerlemesini sorgula (frontend polling icin).

    Celery state'leri:
    - PENDING  : kuyruga alindi, henuz baslamadi
    - STARTED  : worker aldi, basladi
    - PROGRESS : ara bilgi (stage + percent)
    - SUCCESS  : tamam, result icinde ingestion sonucu
    - FAILURE  : hata, error icinde mesaj
    """
    result = AsyncResult(job_id, app=celery_app)

    state = result.state  # "PENDING", "PROGRESS", "SUCCESS", "FAILURE", ...
    payload: dict = {
        "job_id": job_id,
        "state": state,
        "stage": None,
        "percent": None,
        "result": None,
        "error": None,
    }

    if state == "PROGRESS":
        info = result.info or {}
        payload["stage"] = info.get("stage")
        payload["percent"] = info.get("percent")
    elif state == "SUCCESS":
        # result.get() blocking olabilir ama SUCCESS durumunda zaten cache'li
        try:
            payload["result"] = result.get(timeout=1.0)
        except Exception as exc:
            payload["error"] = f"Result alinamadi: {exc}"
    elif state == "FAILURE":
        # info exception objesi olabilir; string'e cevir
        info = result.info
        payload["error"] = str(info) if info else "Bilinmeyen hata"

    return JobStatus(**payload)


# ---------- Eski ingestion endpoint (kaldirildi; artik /upload async) ----------
# IngestionService direkt kullanilmiyor; sadece task uzerinden erisiliyor.


@router.get("/documents/search", response_model=SearchResponse)
async def search(
    q: str,
    top_k: int = 5,
    document_id: str | None = None,
    embedder: BGEEmbedder = Depends(get_embedder_dep),
    vector_store: VectorStore = Depends(get_vector_store),
) -> SearchResponse:
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query bos olamaz.")
    [embedding] = embedder.embed([q])
    hits = vector_store.query(embedding=embedding, top_k=top_k, document_id=document_id)
    return SearchResponse(
        query=q,
        hits=[SearchHit(**h.__dict__) for h in hits],
    )


@router.post("/documents/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    service: RagService = Depends(get_rag_service),
) -> ChatResponse:
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Soru bos olamaz.")
    chunks, answer = service.answer(
        payload.question, payload.document_id, payload.top_k
    )
    return ChatResponse(
        answer=answer,
        sources=[ChatSource(**c.__dict__) for c in chunks],
    )


@router.post("/documents/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    service: RagService = Depends(get_rag_service),
):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Soru bos olamaz.")
    chunks, token_iter = service.stream(
        payload.question, payload.document_id, payload.top_k
    )

    sources_payload = [
        {
            "text": c.text,
            "page_number": c.page_number,
            "document_id": c.document_id,
            "score": c.score,
        }
        for c in chunks
    ]

    def event_iter():
        yield f"event: sources\ndata: {json.dumps(sources_payload)}\n\n"
        for token in token_iter:
            yield f"event: token\ndata: {json.dumps(token)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_iter(),
        media_type="text/event-stream",
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )
