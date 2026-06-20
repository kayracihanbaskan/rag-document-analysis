# RAG (Retrieval-Augmented Generation) servisi:
# 1) Soruyu embedding'e cevir
# 2) Chroma'dan en yakin K chunk'i getir
# 3) Chunk'lari bir "baglam" metnine formatla
# 4) System + user prompt ile LLM'e gonder
# 5) Yanitla birlikte kaynaklari da dondur (frontend'in "N kaynak" detayini gostermesi icin)

from collections.abc import Iterator

from app.core.config import Settings
from app.services.embedder import BGEEmbedder
from app.services.llm import OpenRouterLLM
from app.services.vector_store import RetrievedChunk, VectorStore

SYSTEM_PROMPT = (
    "Sen bir dokuman analiz asistanisin. Asagidaki baglam parcaciklarina dayanarak "
    "kullanicinin sorusunu yanitla. Yanitin yalnizca baglamdaki bilgilere dayansin; "
    "bilmiyorsan 'Kaynaklarda bu bilgi yok' de. Yanitin sonunda kullandigin kaynaklari "
    "kaynak numarasiyla belirt."
)


class RagService:
    def __init__(
        self,
        settings: Settings,
        embedder: BGEEmbedder,
        llm: OpenRouterLLM,
        vector_store: VectorStore,
    ) -> None:
        self._settings = settings
        self._embedder = embedder
        self._llm = llm
        self._vector_store = vector_store

    def _format_context(self, chunks: list[RetrievedChunk]) -> str:
        return "\n\n".join(
            f"[Kaynak {i + 1} | sayfa {c.page_number}]\n{c.text}"
            for i, c in enumerate(chunks)
        )

    def answer(
        self, question: str, document_id: str | None, top_k: int
    ) -> tuple[list[RetrievedChunk], str]:
        [query_embedding] = self._embedder.embed([question])
        chunks = self._vector_store.query(
            embedding=query_embedding, top_k=top_k, document_id=document_id
        )
        context = self._format_context(chunks)
        user_prompt = f"Soru: {question}\n\nBaglam:\n{context}"
        answer = self._llm.complete(SYSTEM_PROMPT, user_prompt)
        return chunks, answer

    def stream(
        self, question: str, document_id: str | None, top_k: int
    ) -> tuple[list[RetrievedChunk], Iterator[str]]:
        [query_embedding] = self._embedder.embed([question])
        chunks = self._vector_store.query(
            embedding=query_embedding, top_k=top_k, document_id=document_id
        )
        context = self._format_context(chunks)
        user_prompt = f"Soru: {question}\n\nBaglam:\n{context}"
        answer_iter = self._llm.stream(SYSTEM_PROMPT, user_prompt)
        return chunks, answer_iter
