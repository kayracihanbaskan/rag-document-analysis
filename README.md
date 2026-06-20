# RAG Document Analysis

PDF dökümanlarını yükleyip içerikleri hakkında Türkçe soru sorabileceğin, kaynak referanslarıyla birlikte yanıt alabileceğin bir **Retrieval-Augmented Generation (RAG)** uygulaması.

![Stack](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white)
![Stack](https://img.shields.io/badge/next.js-15-000000?logo=nextdotjs)
![Stack](https://img.shields.io/badge/fastapi-0.115-009688?logo=fastapi)
![Stack](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Özellikler

- 📄 **PDF ingestion** — `pymupdf` ile dijital PDF'lerden metin çıkarımı
- ✂️ **Recursive chunking** — paragraf → cümle → kelime öncelikli karakter bölücü
- 🧠 **Lokal embedding** — `BAAI/bge-small-en-v1.5` (sentence-transformers, ücretsiz, çevrimdışı)
- 🗄️ **Vector store** — `ChromaDB` (kalıcı, HNSW + cosine)
- 🤖 **LLM** — OpenRouter üzerinden `openai/gpt-4o-mini` (streaming, SSE)
- ⚡ **Backend** — FastAPI + async endpoints
- 🎨 **Frontend** — Next.js 15 + React 19 + Tailwind + Framer Motion (glassmorphism, animasyonlu)
- 📎 **Kaynak şeffaflığı** — Her yanıtta sayfa numarası, chunk metni ve cosine skoru gösterilir

---

## 🏗️ Mimari

```
┌──────────────┐   HTTP    ┌──────────────────┐   OpenAI SDK   ┌────────────┐
│   Next.js    │ ────────▶ │   FastAPI        │ ─────────────▶ │ OpenRouter │
│  (port 3000) │  /api/    │   (port 8000)    │                │  gpt-4o    │
│              │  backend  │                  │                └────────────┘
│  - Upload UI │           │  - PDF parser    │
│  - Chat UI   │           │  - Chunker       │
│  - Doc select│           │  - Embedder      │   sentence-    ┌────────────┐
│              │           │  - RAG service   │ ─transformers─▶│ Chroma     │
│              │           │  - LLM client    │                │ (./data)   │
└──────────────┘           └──────────────────┘                └────────────┘
```

### Akış: Soru sorma

1. Kullanıcı soru yazar → `POST /api/chat` (Next.js)
2. Next.js SSE proxy → `POST /documents/chat/stream` (FastAPI)
3. Backend soruyu BGE ile embed eder
4. Chroma'dan top-K=5 en yakın chunk çekilir
5. System prompt + bağlam + soru → OpenRouter
6. `event: sources` (kaynaklar), `event: token` × N, `event: done` → frontend

### Akış: PDF yükleme

1. `POST /documents/upload` (multipart/form-data)
2. PDF → `pymupdf` → sayfa metinleri
3. `RecursiveCharacterTextSplitter` (chunk_size=800, overlap=120)
4. BGE-small ile batch embedding
5. Chroma'ya `document_id` metadata'sıyla yaz

---

## 📦 Dizin yapısı

```
rag-document-analysis/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── core/config.py       # Pydantic Settings
│   │   ├── api/documents.py     # 4 endpoint
│   │   ├── schemas/documents.py # Pydantic modeller
│   │   └── services/
│   │       ├── pdf_parser.py    # pymupdf
│   │       ├── chunker.py       # Recursive splitter
│   │       ├── embedder.py      # BGE-small
│   │       ├── llm.py           # OpenRouter
│   │       ├── vector_store.py  # Chroma adapter
│   │       ├── ingestion.py     # PDF → DB pipeline
│   │       └── rag.py           # retrieve → prompt → generate
│   ├── data/                    # uploads + chroma (gitignored)
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx         # Landing
    │   │   ├── layout.tsx       # Nav + global bg
    │   │   ├── documents/       # Upload (drag&drop)
    │   │   ├── chat/            # Sohbet
    │   │   └── api/chat/        # SSE proxy
    │   ├── components/
    │   └── lib/
    │       ├── api.ts           # Backend client
    │       ├── storage.ts       # localStorage doc listesi
    │       └── types.ts
    ├── package.json
    ├── tailwind.config.ts
    ├── tsconfig.json
    └── .env.example
```

---

## 🚀 Kurulum

### Önkoşullar

- **Python 3.11** (3.14'te `pymupdf`/`chromadb` wheel yok)
- **Node.js 18.18+** (20.x önerilir)
- OpenRouter hesabı ve API key → https://openrouter.ai/keys

### 1. Backend

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
# .env icindeki OPENROUTER_API_KEY'i doldur
```

### 2. Frontend

```powershell
cd frontend
npm install
copy .env.example .env.local
# .env.local: BACKEND_URL=http://127.0.0.1:8000
```

### 3. Çalıştırma (3 ayrı terminal)

**Terminal 1 — Backend**
```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend**
```powershell
cd frontend
npm run dev
```

**Tarayıcı:** http://localhost:3000

İlk açılışta BGE-small modeli HuggingFace cache'inden indirilir (~120 MB, 1-2 dk). Sonraki açılışlarda anında yüklenir.

---

## 🔌 API

| Method | Path                       | Açıklama                                |
|--------|----------------------------|-----------------------------------------|
| `GET`  | `/health`                  | Health check                            |
| `POST` | `/documents/upload`        | PDF yükle (multipart, `file` field)     |
| `GET`  | `/documents/search?q=...`  | Metin sorgusu, top-K chunk döner        |
| `POST` | `/documents/chat`          | Tam yanıt (kaynak dahil)                |
| `POST` | `/documents/chat/stream`   | SSE streaming: `sources` → `token` × N → `done` |
| `GET`  | `/docs`                    | Swagger UI                              |

### SSE Event Formatı

```
event: sources
data: [{"text":"...","page_number":3,"document_id":"...","score":0.82}]

event: token
data: "Yapay"

event: token
data: " zeka"

event: done
data: {}
```

---

## ⚙️ Konfigürasyon (backend `.env`)

| Değişken                  | Varsayılan                  | Açıklama                              |
|---------------------------|-----------------------------|---------------------------------------|
| `OPENROUTER_API_KEY`      | —                           | OpenRouter key (zorunlu)              |
| `OPENROUTER_BASE_URL`     | `https://openrouter.ai/api/v1` | API base                            |
| `LLM_MODEL`               | `openai/gpt-4o-mini`        | OpenRouter model ID                   |
| `BGE_MODEL_NAME`          | `BAAI/bge-small-en-v1.5`    | sentence-transformers model adı       |
| `BGE_DEVICE`              | `cpu`                       | `cpu` veya `cuda`                     |
| `BGE_BATCH_SIZE`          | `16`                        | Embedding batch boyutu                |
| `CHUNK_SIZE`              | `800`                       | Karakter cinsinden chunk boyutu       |
| `CHUNK_OVERLAP`           | `120`                       | Chunk'lar arası örtüşme               |
| `CHROMA_PERSIST_DIR`      | `./data/chroma`             | Chroma kalıcılık dizini               |
| `MAX_UPLOAD_MB`           | `20`                        | Maks PDF boyutu                       |

---

## 🛠️ Teknoloji seçimlerinin gerekçeleri

- **BGE-small (yerine BGE-M3)**: M3 ~2.3 GB indirme + ~5-15 dk sürüyordu. Small ~120 MB, 1-2 dk. Türkçe kalitesi M3'e göre düşük ama başlangıç için yeterli. İleride tek satır config ile `intfloat/multilingual-e5-base`'e geçilebilir.
- **OpenRouter (yerine doğrudan OpenAI)**: OpenAI bakiyesi bittiğinde bakiye yüklemeden farklı modelleri denemek için. Aynı OpenAI SDK, sadece `base_url` değişiyor.
- **Chroma (yerine Qdrant/Pinecone)**: Tamamen ücretsiz, lokal, sıfır devops. Production scale'e geçerken Qdrant self-host'a migration basit.
- **Recursive splitter (yerine semantik)**: Dil-bağımsız, hızlı, yeterli kalite. Semantik chunking için LlamaIndex `SemanticSplitter` eklenebilir.
- **SSE (yerine WebSocket)**: Tek yönlü iletişim için yeterli, altyapı sadeleşiyor.

---

## 🐛 Bilinen kısıtlar

- Sadece **dijital PDF** (taranmış/imaj PDF'ler için OCR gerekli — `docling` veya `marker` eklenebilir)
- **Auth yok** — şu an tüm dökümanlar ortak. Multi-tenant için JWT eklenmeli.
- **Ingestion senkron** — büyük PDF'ler için arka plan job queue (arq) gerekli.
- **Rate limiting yok** — OpenRouter limitlerine tabi.

---

## 🗺️ Yol haritası

- [ ] OCR (taranmış PDF'ler için)
- [ ] JWT auth + kullanıcı başına döküman izolasyonu
- [ ] `arq` ile async ingestion (queue + progress)
- [ ] Daha iyi Türkçe embedding (`multilingual-e5-base` switch)
- [ ] Qdrant'a migration rehberi
- [ ] Döküman listesi sayfası (silme/yeniden adlandırma)
- [ ] Streaming iptal butonu (AbortController hazır)

---

## 📄 Lisans

MIT
