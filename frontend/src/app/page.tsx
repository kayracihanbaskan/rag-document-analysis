"use client";

import Link from "next/link";
import { motion } from "framer-motion";

const features = [
  {
    title: "PDF yükle",
    desc: "pymupdf ile sayfa metni çıkarılır, BGE-small ile embedding'lere dönüşür, Chroma'ya yazılır.",
    icon: "📄",
  },
  {
    title: "Soru sor",
    desc: "Soru embedding'i ile en yakın K chunk bulunur, OpenRouter üzerinden gpt-4o-mini yanıt üretir.",
    icon: "💬",
  },
  {
    title: "Kaynakları gör",
    desc: "Her yanıtta hangi sayfa ve chunk'tan geldiği gösterilir — halüsinasyonu kendin doğrula.",
    icon: "🔍",
  },
];

export default function HomePage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center"
      >
        <h1 className="text-5xl font-semibold tracking-tight md:text-6xl">
          PDF'lerine{" "}
          <span className="bg-gradient-to-r from-[var(--accent)] to-[var(--accent-2)] bg-clip-text text-transparent">
            doğrudan soru sor
          </span>
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-lg text-muted">
          Retrieval-Augmented Generation ile dökümanlarını yükle, içerik hakkında
          Türkçe sorular sor, kaynak referanslarıyla birlikte yanıt al.
        </p>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mt-8 flex justify-center gap-3"
        >
          <Link
            href="/documents"
            className="glow-on-hover gradient-border inline-flex items-center gap-2 px-5 py-2.5 font-medium text-text"
          >
            <span>📤</span> PDF yükle
          </Link>
          <Link
            href="/chat"
            className="rounded-xl border border-border-strong bg-white/5 px-5 py-2.5 font-medium text-text transition-colors hover:bg-white/10"
          >
            Sohbete git →
          </Link>
        </motion.div>
      </motion.div>

      <div className="mt-20 grid gap-4 md:grid-cols-3">
        {features.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + i * 0.1 }}
            className="glass glow-on-hover rounded-2xl p-6"
          >
            <div className="text-3xl">{f.icon}</div>
            <h3 className="mt-3 font-semibold">{f.title}</h3>
            <p className="mt-2 text-sm text-muted">{f.desc}</p>
          </motion.div>
        ))}
      </div>
    </main>
  );
}
