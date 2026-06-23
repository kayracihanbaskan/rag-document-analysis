"""
Cross-encoder reranker: "retrieve genis, rerank dar" pattern'inin ikinci ayagi.

Embedder (BGE-small) tek seferde en yakin K'i secer. Cross-encoder ise sorgu
ve chunk'i BIRLIKTE okur, "gercekten alakali mi?" diye skor verir. Daha dogru
ama yavas (her chunk icin ayri forward pass).

Neden cross-encoder?
- Bi-encoder (embedding): iki metni ayri vektorlere cevirip cosine similarity
- Cross-encoder: iki metni AYNI MODEL'e birlikte verip direkt skor uretir
  ↑ Bu, tokenlarin etkilesimini gordugu icin cok daha hassas sonuc verir.

Graceful fallback: reranker yuklenemezse veya hata verirse, orijinal retrieve
sonucu oldugu gibi doner. Sistem hicbir zaman durmamali.
"""
import logging
import time
from dataclasses import replace

from sentence_transformers import CrossEncoder

from app.core.config import Settings
from app.services.vector_store import RetrievedChunk

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """BGE-reranker-base (veya baska cross-encoder) ile chunk'lari yeniden siralar."""

    def __init__(self, settings: Settings) -> None:
        self._model_name = settings.rerank_model_name
        self._device = settings.bge_device  # embedder ile ayni device
        try:
            self._model = CrossEncoder(
                self._model_name,
                device=self._device,
                max_length=512,
            )
            logger.info(f"Reranker yuklendi: {self._model_name}")
        except Exception as exc:
            logger.warning(f"Reranker yuklenemedi ({exc}), fallback aktif")
            self._model = None

    @property
    def is_available(self) -> bool:
        return self._model is not None

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Chunk'lari cross-encoder ile yeniden skorla, en iyi top_k'i dondur.

        Reranker'in kendi skoru 0-1 arasidir (logit -> sigmoid). Orijinal
        cosine score yerine bunu kullaniriz, cunku daha kaliteli siralama saglar.
        """
        if not self.is_available or not chunks:
            return chunks[:top_k]

        # CrossEncoder'a [(query, chunk.text), ...] seklinde veriyoruz
        pairs = [(query, c.text) for c in chunks]
        t0 = time.perf_counter()
        try:
            scores = self._model.predict(pairs)
        except Exception as exc:
            logger.warning(f"Rerank sirasinda hata: {exc}, orijinal siralama korunuyor")
            return chunks[:top_k]
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            f"Reranked {len(chunks)} chunks in {elapsed_ms:.0f}ms "
            f"(model={self._model_name})"
        )

        # Sirala (buyukten kucuge), ilk top_k'i al
        scored = sorted(
            zip(chunks, scores),
            key=lambda x: float(x[1]),
            reverse=True,
        )
        reranked: list[RetrievedChunk] = []
        for chunk, score in scored[:top_k]:
            # Orijinal cosine score yerine reranker score'unu yaz
            reranked.append(replace(chunk, score=float(score)))
        return reranked


def get_reranker(settings: Settings) -> CrossEncoderReranker:
    return CrossEncoderReranker(settings)