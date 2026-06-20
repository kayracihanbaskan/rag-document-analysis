# Embedding katmani: metni sayisal vektore donusturur.
# Varsayilan olarak BGE-small-en-v1.5 kullaniyoruz: 384-dim, ~120MB, hizli.
# Daha iyi Turkce kalitesi icin ileride intfloat/multilingual-e5-base veya
# tekrar BAAI/bge-m3'e gecmek mumkun (tek satir config degisikligi).
# Ilk calistirmada model HF cache'inden indirilir, sonra cache'den gelir.

from threading import Lock

from sentence_transformers import SentenceTransformer

from app.core.config import Settings


class BGEEmbedder:
    """Metin listesini 1024-dim vektor listesine cevirir."""

    def __init__(self, settings: Settings) -> None:
        # Model bir kez yuklenir, sonraki cagrilarda cache'den gelir.
        self._model = SentenceTransformer(
            settings.bge_model_name,
            device=settings.bge_device,
        )
        # BGE-M3 8192 token destekler ama RAM/maliyet icin kisaltiyoruz.
        self._model.max_seq_length = settings.bge_max_length
        self._batch_size = settings.bge_batch_size
        # sentence-transformers thread-safe degil; ayni anda birden fazla istek gelirse kilitleriz.
        self._lock = Lock()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        with self._lock:
            vectors = self._model.encode(
                texts,
                batch_size=self._batch_size,
                convert_to_numpy=True,
                # Cosine similarity icin vektorleri L2 normuna normalize ediyoruz;
                # boylece Chroma tarafinda distance = 1 - cos_sim olur, skor 0-1 arasina dusar.
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        return [v.tolist() for v in vectors]


def get_embedder(settings: Settings) -> BGEEmbedder:
    return BGEEmbedder(settings)
