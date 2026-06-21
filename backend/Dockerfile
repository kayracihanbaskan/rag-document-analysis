# syntax=docker/dockerfile:1.7
# Backend Dockerfile - optimize edilmis (sadece CPU wheel, pre-cached BGE).
# Frontend local'de, Redis + backend Docker'da.

FROM python:3.11-slim

# curl: healthcheck icin; tini: PID 1 sinyal yonetimi
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

WORKDIR /app

# Bagimliliklari oncece kopyala (Docker layer cache verimliligi)
COPY requirements.txt .
# --extra-index-url: CPU-only torch (cok daha kucuk, hizli indirme)
# Python 3.11 + CPU torch wheel pre-built; gcc gerekmez
RUN pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements.txt

# BGE modelini build-time'da indir (container her acilista indirmesin)
ARG BGE_MODEL_NAME=BAAI/bge-small-en-v1.5
RUN mkdir -p /home/app/.cache/huggingface && \
    chown -R app:app /home/app/.cache && \
    su app -c "python -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('${BGE_MODEL_NAME}')\""

# Uygulama kodu
COPY --chown=app:app app /app/app
COPY --chown=app:app pyproject.toml ./
USER app

# Persistent volume mount noktasi (compose'da ./data:/app/data)
RUN mkdir -p /app/data/chroma /app/data/uploads && chown -R app:app /app/data

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/home/app/.cache/huggingface

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
