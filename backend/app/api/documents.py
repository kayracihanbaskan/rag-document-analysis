# HTTP katmani: 4 endpoint
# - POST /documents/upload    -> PDF yukle, parse et, embed'le, Chroma'ya yaz
# - GET  /documents/search    -> Metin sorgusu, top-K benzer chunk dondur
# - POST /documents/chat      -> Retrieval + LLM tam yanit (kaynak dahil)
# - POST /documents/chat/stream -> Retrieval + LLM SSE (kaynak + token event'leri)

import json
import shutil
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.schemas.documents import (
    ChatRequest,
    ChatResponse,
    ChatSource,
    IngestResponse,
    SearchHit,
    SearchResponse,
)
from app.services.embedder import BGEEmbedder, get_embedder
from app.services.ingestion import IngestionService
from app.services.llm import OpenRouterLLM, get_llm
from app.services.rag import RagService
from app.services.vector_store import VectorStore

router = APIRouter(prefix="/documents", tags=["documents"])


def get_vector_store(settings: Settings = Depends(get_settings)) -> VectorStore:
    return VectorStore(settings)


def get_embedder_dep(
    settings: Settings = Depends(get_settings),
) -> BGEEmbedder:
    return get_embedder(settings)


def get_llm_dep(settings: Settings = Depends(get_settings)) -> OpenRouterLLM:
    return get_llm(settings)


def get_ingestion_service(
    settings: Settings = Depends(get_settings),
    embedder: BGEEmbedder = Depends(get_embedder_dep),
    vector_store: VectorStore = Depends(get_vector_store),
) -> IngestionService:
    return IngestionService(settings, embedder, vector_store)


def get_rag_service(
    settings: Settings = Depends(get_settings),
    embedder: BGEEmbedder = Depends(get_embedder_dep),
    llm: OpenRouterLLM = Depends(get_llm_dep),
    vector_store: VectorStore = Depends(get_vector_store),
) -> RagService:
    return RagService(settings, embedder, llm, vector_store)


@router.post("/upload", response_model=IngestResponse)
async def upload_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyalari kabul edilir.")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    document_id = str(uuid.uuid4())
    target = settings.upload_dir / f"{document_id}.pdf"

    try:
        with target.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        result = service.ingest(document_id, file.filename, target)
    except ValueError as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    return IngestResponse(**result)


@router.get("/search", response_model=SearchResponse)
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


@router.post("/chat", response_model=ChatResponse)
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


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    service: RagService = Depends(get_rag_service),
):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Soru bos olamaz.")
    chunks, token_iter = service.stream(
        payload.question, payload.document_id, payload.top_k
    )

    # Once kaynaklar tek seferde, sonra token token SSE.
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
