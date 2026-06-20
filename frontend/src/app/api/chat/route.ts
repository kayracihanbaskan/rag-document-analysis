// Next.js -> Backend SSE proxy.
// Frontend'in chat istegini yakalar, son kullanici mesajini cikarir ve
// document_id ile birlikte backend'in /documents/chat/stream endpoint'ine iletir.
// SSE cevabini oldugu gibi frontend'e geri yansitiriz.

import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type IncomingMessage = { role: "user" | "assistant"; content: string };
type IncomingBody = {
  messages: IncomingMessage[];
  document_id?: string | null;
};

export async function POST(req: NextRequest) {
  const body = (await req.json()) as IncomingBody;
  const lastUser = [...(body.messages ?? [])]
    .reverse()
    .find((m) => m.role === "user");
  const question = lastUser?.content ?? "";
  if (!question.trim()) {
    return new Response("Soru bos", { status: 400 });
  }

  const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
  const upstream = await fetch(`${backend}/documents/chat/stream`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      question,
      document_id: body.document_id ?? undefined,
      top_k: 5,
    }),
  });

  if (!upstream.ok || !upstream.body) {
    return new Response("Backend error", { status: 502 });
  }

  // SSE header'lari Next tarafinda da korunmali, yoksa browser buffering yapar
  return new Response(upstream.body, {
    headers: {
      "content-type": "text/event-stream",
      "cache-control": "no-cache",
      "x-accel-buffering": "no",
    },
  });
}
