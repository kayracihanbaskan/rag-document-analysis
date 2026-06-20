# PDF'i sayfa sayfa metne cevirir.
# pymupdf (fitz) kullaniyoruz: hizli, saf Python bagimliligi, OCR gerektirmez (dijital PDF).

from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass
class PageContent:
    page_number: int
    text: str


def parse_pdf(path: Path) -> list[PageContent]:
    pages: list[PageContent] = []
    with pymupdf.open(path) as doc:
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append(PageContent(page_number=index, text=text))
    return pages
