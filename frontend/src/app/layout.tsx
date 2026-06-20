import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";

export const metadata: Metadata = {
  title: "RAG Document Analysis",
  description: "PDF analiz ve soru-cevap",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body className="min-h-screen">
        <nav className="sticky top-0 z-50 glass border-b border-border">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
            <Link href="/" className="flex items-center gap-2 group">
              <span className="inline-block h-7 w-7 rounded-lg bg-gradient-to-br from-[var(--accent)] to-[var(--accent-2)] transition-transform group-hover:rotate-12" />
              <span className="font-semibold tracking-tight">RAG Docs</span>
            </Link>
            <div className="flex gap-1 text-sm">
              <NavLink href="/">Ana sayfa</NavLink>
              <NavLink href="/documents">Dokümanlar</NavLink>
              <NavLink href="/chat">Sohbet</NavLink>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="rounded-lg px-3 py-1.5 text-muted transition-colors hover:bg-white/5 hover:text-text"
    >
      {children}
    </Link>
  );
}
