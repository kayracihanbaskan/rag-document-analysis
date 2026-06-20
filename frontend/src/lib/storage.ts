// Aktif dokuman secimi: hangi PDF uzerinde konustugumuzu tarayicida hatirliyoruz.
// Multi-dokuman destegi icin basit bir liste tutuyoruz; ileride backend'den
// /documents endpoint'i ile liste cekilirse buraya baglanir.

export type StoredDocument = {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
  uploadedAt: string;
};

const KEY_DOCS = "rag.documents";
const KEY_ACTIVE = "rag.activeDocumentId";

function isBrowser() {
  return typeof window !== "undefined";
}

export function listDocuments(): StoredDocument[] {
  if (!isBrowser()) return [];
  try {
    return JSON.parse(localStorage.getItem(KEY_DOCS) ?? "[]") as StoredDocument[];
  } catch {
    return [];
  }
}

export function getActiveDocumentId(): string | null {
  if (!isBrowser()) return null;
  return localStorage.getItem(KEY_ACTIVE);
}

export function getActiveDocument(): StoredDocument | null {
  const id = getActiveDocumentId();
  if (!id) return null;
  return listDocuments().find((d) => d.id === id) ?? null;
}

export function addDocument(doc: StoredDocument): void {
  if (!isBrowser()) return;
  const list = listDocuments();
  // Ayni id yoksa ekle (upload yeniden denenirse tekrara dusmeyelim)
  if (!list.some((d) => d.id === doc.id)) {
    list.unshift(doc);
    localStorage.setItem(KEY_DOCS, JSON.stringify(list));
  }
  // Ilk yuklenen dokuman otomatik aktif olsun
  if (!getActiveDocumentId()) {
    setActiveDocumentId(doc.id);
  }
}

export function setActiveDocumentId(id: string | null): void {
  if (!isBrowser()) return;
  if (id === null) {
    localStorage.removeItem(KEY_ACTIVE);
  } else {
    localStorage.setItem(KEY_ACTIVE, id);
  }
  // Ayni sekmede acik chat sayfasi varsa dinlesin diye event
  window.dispatchEvent(new CustomEvent("rag:active-changed"));
}
