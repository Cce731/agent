"""Extract metadata (title, authors, year, abstract, keywords) from files."""

import re
from pathlib import Path
from typing import Any, Dict, Optional


def _extract_pdf_metadata(path: str) -> Dict[str, Any]:
    """Extract metadata from a PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return {}

    meta: Dict[str, Any] = {}
    try:
        doc = fitz.open(path)
        pdf_meta = doc.metadata or {}

        raw_title = pdf_meta.get("title", "").strip()
        if raw_title:
            meta["title"] = raw_title

        raw_author = pdf_meta.get("author", "").strip()
        if raw_author:
            meta["authors"] = [a.strip() for a in re.split(r"[;,]", raw_author) if a.strip()]

        # Extract year from creation date (format: D:YYYYMMDD...)
        creation = pdf_meta.get("creationDate", "")
        year_match = re.search(r"D:(\d{4})", creation)
        if year_match:
            meta["year"] = int(year_match.group(1))

        # Fall back to text on the first page
        if doc.page_count > 0:
            first_page_text = doc[0].get_text("text")
            meta["first_page_text"] = first_page_text[:3000]

            if "title" not in meta:
                meta["title"] = _guess_title_from_text(first_page_text)

            if "year" not in meta:
                guessed = _guess_year_from_text(first_page_text)
                if guessed:
                    meta["year"] = guessed

            if "abstract" not in meta:
                abstract = _extract_abstract(first_page_text)
                if abstract:
                    meta["abstract"] = abstract

            if "keywords" not in meta:
                keywords = _extract_keywords(first_page_text)
                if keywords:
                    meta["keywords"] = keywords

        doc.close()
    except Exception:
        pass

    return meta


def _extract_docx_metadata(path: str) -> Dict[str, Any]:
    """Extract metadata from a DOCX file."""
    try:
        from docx import Document
        from docx.opc.exceptions import PackageNotFoundError
    except ImportError:
        return {}

    meta: Dict[str, Any] = {}
    try:
        doc = Document(path)
        core = doc.core_properties
        if core.title:
            meta["title"] = core.title.strip()
        if core.author:
            meta["authors"] = [a.strip() for a in re.split(r"[;,]", core.author) if a.strip()]
        if core.created:
            meta["year"] = core.created.year

        full_text = "\n".join(p.text for p in doc.paragraphs)
        meta["first_page_text"] = full_text[:3000]

        if "title" not in meta:
            meta["title"] = _guess_title_from_text(full_text)

        if "abstract" not in meta:
            abstract = _extract_abstract(full_text)
            if abstract:
                meta["abstract"] = abstract

        if "keywords" not in meta:
            keywords = _extract_keywords(full_text)
            if keywords:
                meta["keywords"] = keywords

    except Exception:
        pass

    return meta


def _extract_text_metadata(path: str) -> Dict[str, Any]:
    """Extract metadata from a plain-text or Markdown file."""
    meta: Dict[str, Any] = {}
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = f.read(5000)
        meta["first_page_text"] = text
        meta["title"] = _guess_title_from_text(text)

        year = _guess_year_from_text(text)
        if year:
            meta["year"] = year

        abstract = _extract_abstract(text)
        if abstract:
            meta["abstract"] = abstract

        keywords = _extract_keywords(text)
        if keywords:
            meta["keywords"] = keywords

    except Exception:
        pass

    return meta


def _guess_title_from_text(text: str) -> str:
    """Heuristically guess the title from the first non-empty lines of text."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    # Take the first line that looks like a title (not too long, not too short)
    for line in lines[:5]:
        if 5 < len(line) <= 200:
            return line
    return lines[0][:200] if lines else ""


def _guess_year_from_text(text: str) -> Optional[int]:
    """Look for a plausible publication year in the text."""
    matches = re.findall(r"\b(19[5-9]\d|20[0-2]\d)\b", text)
    if matches:
        return int(matches[0])
    return None


def _extract_abstract(text: str) -> str:
    """Extract the abstract section from the text.

    Requires the word 'Abstract' to appear as a section heading – i.e. at the
    start of a line (optionally followed by a colon/dash and whitespace).
    """
    pattern = re.compile(
        r"(?:^|\n)abstract\s*[:\-]?\s*(.*?)(?=\n(?:keywords?|introduction|1[\.\s]|background)|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(text)
    if m:
        abstract = m.group(1).strip()
        return abstract[:1500]
    return ""


def _extract_keywords(text: str) -> list:
    """Extract the keywords section from the text.

    Requires 'Keywords' to appear as a section heading at the start of a line
    followed by a colon or dash.
    """
    pattern = re.compile(
        r"(?:^|\n)keywords?\s*[:\-]\s*(.*?)(?=\n(?:abstract|introduction|1[\.\s])|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(text)
    if m:
        kw_text = m.group(1).strip().splitlines()[0]  # first line of keywords
        keywords = [k.strip().strip(".") for k in re.split(r"[;,·•]", kw_text) if k.strip()]
        return keywords[:10]
    return []


def extract_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from a file based on its extension.

    Args:
        file_path: Absolute or relative path to the file.

    Returns:
        Dictionary with keys: title, authors, year, abstract, keywords,
        first_page_text (and file_path, file_name, extension always present).
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        meta = _extract_pdf_metadata(file_path)
    elif ext in (".docx", ".doc"):
        meta = _extract_docx_metadata(file_path)
    else:
        meta = _extract_text_metadata(file_path)

    meta["file_path"] = str(path.resolve())
    meta["file_name"] = path.name
    meta["extension"] = ext

    if "title" not in meta or not meta["title"]:
        meta["title"] = path.stem.replace("_", " ").replace("-", " ").title()

    return meta
