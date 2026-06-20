"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

import {
  type StoredDocument,
  getActiveDocument,
  listDocuments,
  setActiveDocumentId,
} from "@/lib/storage";

type Source = {
  text: string;
  page_number: number | null;
  document_id: string;
  score: number;
};

type Msg = { role: "user" | "assistant"; content: string; sources?: Source[] };

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [active, setActive] = useState<StoredDocument | null>(null);
  const [docs, setDocs] = useState<StoredDocument[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const sync = () => {
      setActive(getActiveDocument());
      setDocs(listDocuments());
    };
    sync();
    window.addEventListener("rag:active-changed", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("rag:active-changed", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  // Yeni mesaj geldiginde asagi kaydir
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, busy]);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    const userMsg: Msg = { role: "user", content: text };
    const assistantMsg: Msg = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setBusy(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: text }],
          document_id: active?.id ?? null,
        }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let idx: number;
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const raw = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const lines = raw.split("\n");
          let event = "message";
          let data = "";
          for (const line of lines) {
            if (line.startsWith("event: ")) event = line.slice(7).trim();
            else if (line.startsWith("data: ")) data += line.slice(6);
          }
          if (event === "sources" && data) {
            try {
              const sources = JSON.parse(data) as Source[];
              setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = { ...copy[copy.length - 1], sources };
                return copy;
              });
            } catch {}
          } else if (event === "token" && data) {
            try {
              const token = JSON.parse(data) as string;
              setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = {
                  ...copy[copy.length - 1],
                  content: copy[copy.length - 1].content + token,
                };
                return copy;
              });
            } catch {}
          }
        }
      }
    } catch (err) {
      setMessages((prev) => {
        const copy = [...prev];
        copy[copy.length - 1] = {
          ...copy[copy.length - 1],
          content:
            copy[copy.length - 1].content ||
            `(hata: ${(err as Error).message})`,
        };
        return copy;
      });
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col px-4 py-6 h-[calc(100vh-65px)]">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4 flex items-center justify-between gap-3"
      >
        <h1 className="text-2xl font-semibold tracking-tight">Sohbet</h1>
        <DocSelector docs={docs} active={active} onChange={setActiveDocumentId} />
      </motion.div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto rounded-2xl glass p-4 space-y-4"
      >
        {messages.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex h-full flex-col items-center justify-center text-center"
          >
            <div className="text-5xl">💬</div>
            <p className="mt-4 text-muted">
              {active
                ? `"${active.filename}" hakkinda soru sor.`
                : "Bir PDF yukledikten sonra icerigi hakkinda soru sorabilirsin."}
            </p>
          </motion.div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.25 }}
              className="space-y-1"
            >
              <div
                className={`rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
                  m.role === "user"
                    ? "ml-12 bg-gradient-to-br from-[var(--accent)] to-[var(--accent-2)] text-bg font-medium shadow-lg shadow-[var(--accent)]/20"
                    : "mr-12 glass border border-border"
                }`}
              >
                {m.content ||
                  (m.role === "assistant" && busy && i === messages.length - 1 ? (
                    <TypingIndicator />
                  ) : (
                    ""
                  ))}
              </div>

              {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                <motion.details
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="mr-12 ml-2 overflow-hidden text-xs"
                >
                  <summary className="cursor-pointer select-none rounded-lg px-2 py-1 text-muted transition-colors hover:bg-white/5 hover:text-text">
                    📎 {m.sources.length} kaynak
                  </summary>
                  <ul className="mt-2 space-y-1.5">
                    {m.sources.map((s, j) => (
                      <motion.li
                        key={j}
                        initial={{ opacity: 0, x: -5 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: j * 0.05 }}
                        className="rounded-lg border border-border bg-bg/60 p-2.5 backdrop-blur"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-[var(--accent)]">
                            Sayfa {s.page_number ?? "?"}
                          </span>
                          <span className="text-muted">
                            Skor: {(s.score * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="mt-1 text-text/80">{s.text}</p>
                      </motion.li>
                    ))}
                  </ul>
                </motion.details>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <motion.form
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="mt-4 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            active
              ? `${active.filename} hakkinda bir soru...`
              : "Once bir PDF yukle..."
          }
          className="flex-1 rounded-xl border border-border bg-surface px-4 py-3 text-sm outline-none transition-colors placeholder:text-muted focus:border-[var(--accent)]"
        />
        <motion.button
          whileHover={{ scale: busy ? 1 : 1.03 }}
          whileTap={{ scale: 0.97 }}
          disabled={busy}
          className="gradient-border glow-on-hover px-5 py-3 font-medium text-text disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? "..." : "Gonder"}
        </motion.button>
      </motion.form>
    </main>
  );
}

function TypingIndicator() {
  return (
    <span aria-label="Yanit uretiliyor">
      <span className="typing-dot" />
      <span className="typing-dot" />
      <span className="typing-dot" />
    </span>
  );
}

function DocSelector({
  docs,
  active,
  onChange,
}: {
  docs: StoredDocument[];
  active: StoredDocument | null;
  onChange: (id: string | null) => void;
}) {
  if (docs.length === 0) {
    return (
      <a
        href="/documents"
        className="rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-[var(--accent)] transition-colors hover:bg-[var(--accent)]/10"
      >
        + Dokuman yukle
      </a>
    );
  }
  return (
    <select
      value={active?.id ?? ""}
      onChange={(e) => onChange(e.target.value || null)}
      className="max-w-[240px] rounded-lg border border-border bg-surface px-3 py-1.5 text-sm transition-colors focus:border-[var(--accent)] focus:outline-none"
      title="Aktif dokuman"
    >
      <option value="">Tum dokumanlar</option>
      {docs.map((d) => (
        <option key={d.id} value={d.id}>
          {d.filename}
        </option>
      ))}
    </select>
  );
}
