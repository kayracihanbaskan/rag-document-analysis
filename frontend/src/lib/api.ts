// Backend'e yapilan HTTP cagrilari. Next.js rewrite kurali sayesinde
// /api/backend/* -> BACKEND_URL/* seklinde proxy'leniyor (next.config.ts).

import type { ChatResponse, IngestResponse, SearchResponse } from "./types";

const BASE = "/api/backend";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadDocument(file: File): Promise<IngestResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/documents/upload`, { method: "POST", body: form });
  return handle<IngestResponse>(res);
}

export async function search(
  q: string,
  documentId?: string | null,
  topK = 5
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, top_k: String(topK) });
  if (documentId) params.set("document_id", documentId);
  const res = await fetch(`${BASE}/documents/search?${params}`);
  return handle<SearchResponse>(res);
}

// document_id opsiyonel; bossa backend tum dokumanlardan arar.
export async function chat(
  question: string,
  documentId?: string | null,
  topK = 5
): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/documents/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      question,
      document_id: documentId ?? undefined,
      top_k: topK,
    }),
  });
  return handle<ChatResponse>(res);
}
