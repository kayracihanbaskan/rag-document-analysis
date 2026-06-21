# Guvenlik katmanlari (prompt injection'a karsi).
# Uc katman var: input sanitization (ingestion'da), input regex (chat'te),
# output filter (LLM yanitinda). Tek tek ne yaptiklari asagida.

import re
from dataclasses import dataclass


# --- 1. Input sanitization (chunk seviyesinde, ingestion sirasinda) ---

# Prompt injection'da sik kullanilan kalip ifadeleri.
# Compile edilmis regex'ler - hizli kontrol.
_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore (?:all )?(?:previous|prior|above) (?:instructions?|prompts?)"),
    re.compile(r"(?i)disregard (?:the )?(?:system|previous) (?:prompt|message)"),
    re.compile(r"(?i)you are (?:now|actually) (?:a|an)"),
    re.compile(r"(?i)forget (?:everything|all)"),
    re.compile(r"(?i)new (?:role|system) prompt"),
    re.compile(r"<\|.*?\|>"),                       # Ozel token enjeksiyonu
    re.compile(r"###\s*(?:system|instruction)"),   # Markdown'a gizlenmis
    re.compile(r"\[INST\]|\[/INST\]"),              # Llama formatinda gizleme
]

# Gizli API key / token sizintisi
_SECRET_LIKE = re.compile(
    r"(sk-[a-zA-Z0-9]{16,}|sk-or-v1-[a-zA-Z0-9]{16,}|sk-[a-zA-Z0-9]{20,})"
)


@dataclass
class SanitizationResult:
    text: str          # Temizlenmis metin (veya orijinal)
    blocked: bool      # Tamamen bloklandi mi
    reason: str | None = None


def sanitize_chunk_for_storage(text: str) -> SanitizationResult:
    """PDF'ten gelen metin Chroma'ya yazilmadan once temizlenir.

    - Asiri uzun chunk (>5000 karakter) bloklanir (padding saldirisi)
    - Prompt injection kaliplari varsa yerine "[supspect]" yazilir
    - API key benzeri desenler maskelenir
    - Tamamen talimat iceren chunk'lar (sadece keyword'lerden olusan) bloklanir

    Bu ucuz ve hizli bir savunma katmanidir; LLM'in gormeden once ilk filtredir.
    """
    if not text or not text.strip():
        return SanitizationResult(text="", blocked=True, reason="bos")

    if len(text) > 5000:
        return SanitizationResult(text="", blocked=True, reason="asiri uzunluk (padding)")

    cleaned = text

    # 1. Prompt injection kaliplari: yakalanirsa o satiri placeholder ile degistir
    for pat in _INJECTION_PATTERNS:
        cleaned = pat.sub("[icerik kaldirildi - prompt injection]", cleaned)

    # 2. Gizli API key / token desenleri maskelenir
    cleaned = _SECRET_LIKE.sub("[API_KEY_KALDIRILDI]", cleaned)

    # 3. Chunk'in tamami sadece talimat icerigi mi? (chunk'in %60'i kaliplardan olusuyorsa)
    total_chars = len(cleaned)
    suspicious_chars = sum(len(m.group()) for m in _INJECTION_PATTERNS[0].finditer(cleaned))
    if total_chars > 0 and suspicious_chars / total_chars > 0.5:
        return SanitizationResult(text="", blocked=True, reason="chunk yogunlukla talimat")

    return SanitizationResult(text=cleaned, blocked=False)


# --- 2. Input guardrails (kullanici sorusu seviyesinde) ---

_USER_INPUT_PATTERNS = [
    re.compile(r"(?i)what(?:'s| is) your (?:system )?prompt"),
    re.compile(r"(?i)show (?:me )?your (?:system )?(?:prompt|instructions?)"),
    re.compile(r"(?i)reveal your (?:system )?(?:prompt|instructions?)"),
    re.compile(r"(?i)repeat (?:your )?(?:system )?(?:prompt|instructions?)"),
    re.compile(r"(?i)ignore (?:all )?(?:previous|prior|safety)"),
    re.compile(r"(?i)act as (?:a|an)?(?:different|new)"),
    re.compile(r"(?i)dan mode|jailbreak"),
    re.compile(r"(?i)developer mode|god mode"),
]


def is_user_input_safe(text: str) -> tuple[bool, str | None]:
    """Kullanici sorusunu chat'ten once kontrol et. Supheli ise reddet.

    Returns: (safe, reason)
    """
    for pat in _USER_INPUT_PATTERNS:
        if pat.search(text):
            return False, "Supheli komut tespit edildi (prompt injection denemesi)."
    return True, None


# --- 3. Output filter (LLM yanitinda) ---

_OUTPUT_FORBIDDEN = [
    re.compile(r"sk-[a-zA-Z0-9]{16,}"),                  # OpenAI key
    re.compile(r"sk-or-v1-[a-zA-Z0-9]{16,}"),            # OpenRouter key
    re.compile(r"(?i)(?:my|the) (?:system )?prompt (?:is|says)"),  # Prompt ifsa
    re.compile(r"(?i)I am (?:a|an) (?:chatbot|AI) (?:developed|made) by"),
]


def sanitize_response(text: str) -> str:
    """LLM yanitinda API key / prompt ifsa kontrolu. Bulursa maskele veya reddet.

    Bu ucuz bir kontroldur; akilli saldirilari yakalamaz ama en sik olanlari durdurur.
    """
    cleaned = text
    for pat in _OUTPUT_FORBIDDEN:
        cleaned = pat.sub("[GUVENLIK: Bu icerik paylasilamaz]", cleaned)
    return cleaned
