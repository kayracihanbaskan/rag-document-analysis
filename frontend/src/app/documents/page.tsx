"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type DragEvent } from "react";

import { getJobStatus, uploadDocument } from "@/lib/api";
import { addDocument } from "@/lib/storage";
import type { JobStatus } from "@/lib/types";

// Ingestion durumlarina gore UI metni
function describeJob(s: JobStatus): { label: string; tone: "wait" | "ok" | "err" } {
  if (s.state === "FAILURE") return { label: s.error || "Hata olustu", tone: "err" };
  if (s.state === "SUCCESS") {
    const r = s.result;
    return { label: `${r?.filename}: ${r?.pages} sayfa, ${r?.chunks} chunk`, tone: "ok" };
  }
  if (s.state === "PROGRESS") return { label: s.stage || "Isleniyor...", tone: "wait" };
  if (s.state === "STARTED") return { label: "Worker basladi...", tone: "wait" };
  return { label: "Kuyruga alindi...", tone: "wait" };
}

export default function DocumentsPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Polling: job SUCCESS veya FAILURE olunca durur
  useEffect(() => {
    if (!job || job.state === "SUCCESS" || job.state === "FAILURE") return;
    const t = setInterval(async () => {
      try {
        const s = await getJobStatus(job.job_id);
        setJob(s);
        if (s.state === "SUCCESS" && s.result) {
          addDocument({
            id: s.result.document_id,
            filename: s.result.filename,
            pages: s.result.pages,
            chunks: s.result.chunks,
            uploadedAt: new Date().toISOString(),
          });
          // Chat'e otomatik gec (kullanici mesaji okusun diye 800ms bekle)
          setTimeout(() => router.push("/chat"), 800);
        }
      } catch {
        // backend gecici olarak cevap vermezse yeniden dene
      }
    }, 1000);
    return () => clearInterval(t);
  }, [job, router]);

  function handleFile(f: File | undefined | null) {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setErrMsg("Sadece PDF dosyasi kabul edilir.");
      return;
    }
    setFile(f);
    setJob(null);
    setErrMsg(null);
  }

  function onDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  }

  async function onUpload() {
    if (!file || job) return;
    setErrMsg(null);
    try {
      const accepted = await uploadDocument(file);
      // Henuz polling baslamadi; PENDING state'ini goster
      setJob({
        job_id: accepted.job_id,
        state: "PENDING",
        stage: "Kuyruga alindi, worker bekleniyor...",
        percent: null,
        result: null,
        error: null,
      });
    } catch (err) {
      setErrMsg((err as Error).message);
    }
  }

  const busy = !!job && job.state !== "SUCCESS" && job.state !== "FAILURE";
  const jobDesc = job ? describeJob(job) : null;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <motion.h1
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-3xl font-semibold tracking-tight"
      >
        PDF Yukle
      </motion.h1>
      <p className="mt-2 text-muted">
        Digital bir PDF sec. Ingestion arka planda calisir, ilerlemeyi asagidan takip edebilirsin.
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
          } ${busy ? "pointer-events-none opacity-50" : ""}`}
        >
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => handleFile(e.target.files?.[0])}
            className="hidden"
            disabled={busy}
          />
          <motion.div animate={{ y: dragOver ? -4 : 0 }} className="text-4xl">
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
            whileHover={{ scale: !file || busy ? 1 : 1.02 }}
            whileTap={{ scale: 0.98 }}
            disabled={!file || busy}
            onClick={onUpload}
            className="gradient-border glow-on-hover relative inline-flex items-center gap-2 px-5 py-2.5 font-medium text-text disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy && <Spinner />}
            {busy ? "Isleniyor..." : "Yukle"}
          </motion.button>

          {file && !busy && (
            <button
              onClick={() => {
                setFile(null);
                setJob(null);
                setErrMsg(null);
              }}
              className="text-sm text-muted hover:text-text"
            >
              Iptal
            </button>
          )}
        </div>

        {/* Job durumu: ilerleme cubugu + mesaj */}
        <AnimatePresence mode="wait">
          {job && jobDesc && (
            <motion.div
              key={job.state + (job.percent ?? "")}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              className="mt-5 rounded-xl border border-border bg-surface p-4"
            >
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-muted">{job.state}</span>
                {job.percent !== null && (
                  <span className="text-muted">%{job.percent}</span>
                )}
              </div>
              <p className={`mt-2 text-sm ${jobDesc.tone === "err" ? "text-[var(--danger)]" : jobDesc.tone === "ok" ? "text-[var(--success)]" : "text-text"}`}>
                {jobDesc.tone === "ok" && "✓ "}
                {jobDesc.tone === "err" && "✗ "}
                {jobDesc.label}
              </p>
              {/* Determinate progress bar (varsa yuzde), indeterminate spinner (yoksa) */}
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/5">
                {job.percent !== null ? (
                  <motion.div
                    className="h-full bg-gradient-to-r from-[var(--accent)] to-[var(--accent-2)]"
                    initial={{ width: 0 }}
                    animate={{ width: `${job.percent}%` }}
                    transition={{ duration: 0.4 }}
                  />
                ) : (
                  <motion.div
                    className="h-full w-1/3 bg-gradient-to-r from-[var(--accent)] to-[var(--accent-2)]"
                    animate={{ x: ["-100%", "300%"] }}
                    transition={{ repeat: Infinity, duration: 1.4, ease: "easeInOut" }}
                  />
                )}
              </div>
            </motion.div>
          )}

          {errMsg && (
            <motion.p
              key="err"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="mt-4 text-sm text-[var(--danger)]"
            >
              ✗ {errMsg}
            </motion.p>
          )}
        </AnimatePresence>
      </motion.div>
    </main>
  );
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}
