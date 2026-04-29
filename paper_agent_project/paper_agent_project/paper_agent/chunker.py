from __future__ import annotations

import re
from dataclasses import dataclass

from .utils import normalize_space, stable_id


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    index: int
    page_start: int | None = None
    page_end: int | None = None


def split_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
    """Split text into overlapping chunks. Works for Chinese and English."""
    text = text.strip()
    if not text:
        return []

    # Prefer paragraph boundaries first.
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}".strip()
            continue
        if current:
            chunks.append(current)
            tail = current[-overlap:] if overlap > 0 else ""
            current = f"{tail}\n\n{para}".strip()
        else:
            # Very long paragraph: split by characters.
            start = 0
            while start < len(para):
                end = start + chunk_size
                chunks.append(para[start:end])
                start = max(end - overlap, end)
            current = ""

    if current:
        chunks.append(current)

    return [normalize_space(c) for c in chunks if c.strip()]


def chunks_from_pages(doc_id: str, pages: list[str], chunk_size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    idx = 0
    for page_no, page_text in enumerate(pages, start=1):
        for text in split_text(page_text, chunk_size, overlap):
            chunk_id = stable_id(f"{doc_id}:{idx}:{text}")
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    text=text,
                    index=idx,
                    page_start=page_no,
                    page_end=page_no,
                )
            )
            idx += 1
    return chunks
