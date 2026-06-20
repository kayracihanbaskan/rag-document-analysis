# Recursive karakter splitter: metni once paragraf, sonra satir, sonra cumle, sonra kelime
# sinirlarindan keserek yaklasik chunk_size'a kadar parcalar.
# Dil-bagimsiz calisir; Turkce icin ayarlanmis separator oncelikleri yeterli.

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class Chunk:
    text: str
    page_number: int
    chunk_index: int


def split_pages(
    pages: list, chunk_size: int, chunk_overlap: int
) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        # "." ve "?" oncelikli ki cumle ortasinda kesilmesin.
        separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
    )
    chunks: list[Chunk] = []
    chunk_index = 0
    for page in pages:
        for piece in splitter.split_text(page.text):
            text = piece.strip()
            if not text:
                continue
            chunks.append(
                Chunk(
                    text=text,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1
    return chunks
