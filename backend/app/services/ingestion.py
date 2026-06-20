# Ingestion pipeline: PDF -> sayfalar -> chunk'lar -> embedding'ler -> Chroma.
# Tek seferde calisan, streaming olmayan, basit orkestrasyon.

from pathlib import Path

from app.core.config import Settings
from app.services.chunker import split_pages
from app.services.embedder import BGEEmbedder
from app.services.pdf_parser import parse_pdf
from app.services.vector_store import VectorStore


class IngestionService:
    def __init__(
        self,
        settings: Settings,
        embedder: BGEEmbedder,
        vector_store: VectorStore,
    ) -> None:
        self._settings = settings
        self._embedder = embedder
        self._vector_store = vector_store

    def ingest(self, document_id: str, filename: str, pdf_path: Path) -> dict:
        # 1) PDF'i sayfa sayfa oku
        pages = parse_pdf(pdf_path)
        if not pages:
            raise ValueError("PDF icinde metin bulunamadi.")

        # 2) Her sayfayi recursive karakter splitter ile chunk'la
        chunks = split_pages(
            pages,
            chunk_size=self._settings.chunk_size,
            chunk_overlap=self._settings.chunk_overlap,
        )
        if not chunks:
            raise ValueError("Chunking sonrasi icerik uretilemedi.")

        # 3) Chunk'lari BGE-M3 ile vektore cevir
        embeddings = self._embedder.embed([c.text for c in chunks])

        # 4) Chroma'ya yaz (document_id ile metadata'da izole ediliyor)
        stored = self._vector_store.add(document_id, filename, chunks, embeddings)

        return {
            "document_id": document_id,
            "filename": filename,
            "pages": len(pages),
            "chunks": stored,
        }
