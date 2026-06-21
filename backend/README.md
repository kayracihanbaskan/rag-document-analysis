---
title: RAG Document Analysis
emoji: 📄
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# RAG Document Analysis — Backend

Bu Space, [kayracihanbaskan/rag-document-analysis](https://github.com/kayracihanbaskan/rag-document-analysis) reposunun backend'ini çalıştırır.

## Endpointler

- `GET  /health`
- `POST /documents/upload` — multipart, `file` field
- `GET  /jobs/{job_id}` — task ilerlemesi
- `GET  /documents/search?q=...`
- `POST /documents/chat`
- `POST /documents/chat/stream` — SSE

## Konfigürasyon

Space ayarlarından **Repository secrets** kısmına `OPENROUTER_API_KEY` ekle.

## Veri kalıcılığı

`/data` klasörü (Chroma + uploads) Space yeniden başlatılsa bile korunur.
