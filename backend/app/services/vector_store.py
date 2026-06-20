# Vector store adaptoru: Chroma'yi basit bir API arkasina gizliyoruz.
# Chroma HNSW index'i ile cosine distance kullanir; metadata ile filtreleme (document_id) yapabilir.
# distance degeri 0 = ayni, 2 = zit vektor; biz 1 - distance yaparak 0-1 arasi benzerlik skoru uretiyoruz.

import uuid
from dataclasses import dataclass
from pathlib import Path

import chromadb

from app.core.config import Settings


@dataclass
class RetrievedChunk:
    text: str
    page_number: int | None
    document_id: str
    score: float


class VectorStore:
    def __init__(self, settings: Settings) -> None:
        settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(settings.chroma_persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    def add(
        self,
        document_id: str,
        filename: str,
        chunks: list,
        embeddings: list[list[float]],
    ) -> int:
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []
        for chunk, embedding in zip(chunks, embeddings):
            ids.append(str(uuid.uuid4()))
            documents.append(chunk.text)
            metadatas.append(
                {
                    "document_id": document_id,
                    "filename": filename,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                }
            )
        self._collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(ids)

    def query(
        self,
        embedding: list[float],
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[RetrievedChunk]:
        where = {"document_id": document_id} if document_id else None
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
        )
        hits: list[RetrievedChunk] = []
        for doc, meta, distance in zip(
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        ):
            hits.append(
                RetrievedChunk(
                    text=doc,
                    page_number=meta.get("page_number"),
                    document_id=meta["document_id"],
                    score=1.0 - float(distance),
                )
            )
        return hits

    def delete_document(self, document_id: str) -> None:
        self._collection.delete(where={"document_id": document_id})
