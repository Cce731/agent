from __future__ import annotations

import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .chunker import Chunk
from .utils import ensure_dir, read_json, write_json


@dataclass
class DocumentRecord:
    doc_id: str
    path: str
    filename: str
    suffix: str
    title: str
    sha256: str
    text_length: int
    chunk_count: int


@dataclass
class SearchResult:
    score: float
    chunk_id: str
    doc_id: str
    title: str
    filename: str
    text: str
    page_start: int | None
    page_end: int | None


class KnowledgeStore:
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        ensure_dir(storage_dir)
        self.docs_path = storage_dir / "documents.json"
        self.chunks_path = storage_dir / "chunks.json"
        self.index_path = storage_dir / "tfidf_index.pkl"

        self.documents: dict[str, dict[str, Any]] = read_json(self.docs_path, {})
        self.chunks: dict[str, dict[str, Any]] = read_json(self.chunks_path, {})
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        self.chunk_order: list[str] = []
        self._load_index()

    def save(self) -> None:
        write_json(self.docs_path, self.documents)
        write_json(self.chunks_path, self.chunks)

    def _load_index(self) -> None:
        if not self.index_path.exists():
            return
        try:
            with self.index_path.open("rb") as f:
                payload = pickle.load(f)
            self.vectorizer = payload.get("vectorizer")
            self.matrix = payload.get("matrix")
            self.chunk_order = payload.get("chunk_order", [])
        except Exception:
            self.vectorizer = None
            self.matrix = None
            self.chunk_order = []

    def rebuild_index(self) -> None:
        texts = []
        chunk_order = []
        for chunk_id, chunk in self.chunks.items():
            if chunk.get("text", "").strip():
                chunk_order.append(chunk_id)
                texts.append(chunk["text"])

        if not texts:
            self.vectorizer = None
            self.matrix = None
            self.chunk_order = []
            return

        # char_wb works well enough for mixed Chinese / English without extra tokenizer.
        vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            min_df=1,
            max_features=60000,
        )
        matrix = vectorizer.fit_transform(texts)
        self.vectorizer = vectorizer
        self.matrix = matrix
        self.chunk_order = chunk_order

        with self.index_path.open("wb") as f:
            pickle.dump(
                {"vectorizer": vectorizer, "matrix": matrix, "chunk_order": chunk_order},
                f,
            )

    def upsert_document(self, record: DocumentRecord, chunks: list[Chunk]) -> None:
        # Remove old chunks for this document first.
        old_chunk_ids = [cid for cid, c in self.chunks.items() if c.get("doc_id") == record.doc_id]
        for cid in old_chunk_ids:
            self.chunks.pop(cid, None)

        self.documents[record.doc_id] = asdict(record)
        for chunk in chunks:
            self.chunks[chunk.chunk_id] = asdict(chunk)
        self.save()

    def search(self, query: str, top_k: int = 6) -> list[SearchResult]:
        if not self.vectorizer or self.matrix is None or not self.chunk_order:
            self.rebuild_index()
        if not self.vectorizer or self.matrix is None:
            return []

        q_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self.matrix).ravel()
        if scores.size == 0:
            return []

        top_indices = np.argsort(scores)[::-1][:top_k]
        results: list[SearchResult] = []
        for i in top_indices:
            score = float(scores[i])
            if score <= 0:
                continue
            chunk_id = self.chunk_order[int(i)]
            chunk = self.chunks[chunk_id]
            doc = self.documents.get(chunk["doc_id"], {})
            results.append(
                SearchResult(
                    score=score,
                    chunk_id=chunk_id,
                    doc_id=chunk["doc_id"],
                    title=doc.get("title", ""),
                    filename=doc.get("filename", ""),
                    text=chunk.get("text", ""),
                    page_start=chunk.get("page_start"),
                    page_end=chunk.get("page_end"),
                )
            )
        return results

    def get_doc_chunks(self, doc_id: str, limit_chars: int = 16000) -> str:
        selected = [c for c in self.chunks.values() if c.get("doc_id") == doc_id]
        selected.sort(key=lambda x: x.get("index", 0))
        text = "\n\n".join(c.get("text", "") for c in selected)
        return text[:limit_chars]

    def stats(self) -> dict[str, int]:
        return {"documents": len(self.documents), "chunks": len(self.chunks)}
