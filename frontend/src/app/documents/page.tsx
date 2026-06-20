"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { useState, type DragEvent } from "react";

import { uploadDocument } from "@/lib/api";
import { addDocument } from "@/lib/storage";

type UploadState = "idle" | "uploading" | "success" | "error";

export default function DocumentsPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [message, setMessage] = useState("");
  const [dragOver, setDragOver] = useState(false);

  function handleFile(f: File | undefined | null) {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setState("error");
      setMessage("Sadece PDF dosyasi kabul edilir.");
      return;
    }
    setFile(f);
    setState("idle");
    setMessage("");
  }

  function onDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  }

  async function onUpload() {
    if (!file) return;
    setState("uploading");
    setMessage("PDF okunuyor, chunk'lanıyor ve embedding'leniyor...");
    try {
      const result = await uploadDocument(file);
      addDocument({
        id: result.document_id,
        filename: result.filename,
        pages: result.pages,
        chunks: result.chunks,
        uploadedAt: new Date().toISOString(),
      });
      setState("success");
      setMessage(`${result.filename}: ${result.pages} sayfa, ${result.chunks} chunk.`);
      setTimeout(() => router.push("/chat"), 900);
    } catch (err) {
      setState("error");
      setMessage(`Hata: ${(err as Error).message}`);
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <motion.h1
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-3xl font-semibold tracking-tight"
      >
        PDF Yükle
      </motion.h1>
      <p className="mt-2 text-muted">
        Digital bir PDF sec (taranmis/imaj PDF'ler icin OCR gerekli, simdilik desteklenmiyor).
      </p>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mt-8"
      >
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          className={`glass flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-12 text-center transition-all ${
            dragOver
              ? "border-[var(--accent)] bg-[var(--accent)]/5 scale-[1.02]"
              : "border-border hover:border-border-strong"
          }`}
        >
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => handleFile(e.target.files?.[0])}
            className="hidden"
          />
          <motion.div
            animate={{ y: dragOver ? -4 : 0 }}
            className="text-4xl"
          >
            {file ? "📄" : "📥"}
          </motion.div>
          <p className="mt-3 font-medium">
            {file ? file.name : "PDF'i buraya surukle veya tikla"}
          </p>
          <p className="mt-1 text-xs text-muted">
            {file ? `${(file.size / 1024).toFixed(0)} KB` : "Maks. 20 MB"}
          </p>
        </label>

        <div className="mt-5 flex items-center gap-3">
          <motion.button
            whileHover={{ scale: file && state !== "uploading" ? 1.02 : 1 }}
            whileTap={{ scale: 0.98 }}
            disabled={!file || state === "uploading"}
            onClick={onUpload}
            className="gradient-border glow-on-hover relative inline-flex items-center gap-2 px-5 py-2.5 font-medium text-text disabled:cursor-not-allowed disabled:opacity-40"
          >
            {state === "uploading" && (
              <Spinner />
            )}
            {state === "success" ? "Yuklendi" : state === "uploading" ? "Isleniyor..." : "Yukle"}
          </motion.button>

          {file && state !== "uploading" && (
            <button
              onClick={() => {
                setFile(null);
                setState("idle");
                setMessage("");
              }}
              className="text-sm text-muted hover:text-text"
            >
              Iptal
            </button>
          )}
        </div>

        <AnimatePresence mode="wait">
          {message && (
            <motion.p
              key={state + message}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              className={`mt-4 text-sm ${
                state === "error"
                  ? "text-[var(--danger)]"
                  : state === "success"
                    ? "text-[var(--success)]"
                    : "text-muted"
              }`}
            >
              {state === "success" && "✓ "}
              {state === "error" && "✗ "}
              {message}
            </motion.p>
          )}
        </AnimatePresence>
      </motion.div>
    </main>
  );
}

function Spinner() {
  return (
    <svg
      className="h-4 w-4 animate-spin"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeOpacity="0.25"
        strokeWidth="3"
      />
      <path
        d="M22 12a10 10 0 0 1-10 10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}
