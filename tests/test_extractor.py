"""Tests for metadata extraction."""

from pathlib import Path

import pytest

from src.extractor import (
    _extract_abstract,
    _extract_keywords,
    _guess_title_from_text,
    _guess_year_from_text,
    extract_metadata,
)


class TestHelpers:
    def test_guess_title_simple(self):
        text = "Deep Learning for Natural Language Processing\nAuthors: John Doe\nAbstract:"
        assert _guess_title_from_text(text) == "Deep Learning for Natural Language Processing"

    def test_guess_title_skips_empty_lines(self):
        text = "\n\nA Novel Approach\nOther text"
        assert _guess_title_from_text(text) == "A Novel Approach"

    def test_guess_title_empty(self):
        assert _guess_title_from_text("") == ""

    def test_guess_year_found(self):
        assert _guess_year_from_text("Published in 2021, this paper...") == 2021

    def test_guess_year_older_paper(self):
        assert _guess_year_from_text("Originally published 1985 in IEEE...") == 1985

    def test_guess_year_not_found(self):
        assert _guess_year_from_text("No year here at all.") is None

    def test_guess_year_ignores_unrealistic(self):
        # 1234 is not in the 19xx/20xx range
        assert _guess_year_from_text("Year 1234 was long ago.") is None

    def test_extract_abstract(self):
        text = "Title\nAbstract: This paper proposes a new method.\nKeywords: deep learning"
        assert "new method" in _extract_abstract(text)

    def test_extract_abstract_missing(self):
        assert _extract_abstract("No abstract here.") == ""

    def test_extract_keywords(self):
        text = "Abstract: ...\nKeywords: neural network, transformer, NLP\nIntroduction"
        kws = _extract_keywords(text)
        assert "neural network" in kws
        assert "transformer" in kws

    def test_extract_keywords_missing(self):
        assert _extract_keywords("No keywords here.") == []


class TestExtractMetadata:
    def test_txt_file(self, tmp_path):
        f = tmp_path / "paper.txt"
        f.write_text(
            "A Study on Deep Learning\nAuthors: Alice\n"
            "Abstract: We study deep learning.\nKeywords: deep learning, AI\n",
            encoding="utf-8",
        )
        meta = extract_metadata(str(f))
        assert meta["file_name"] == "paper.txt"
        assert meta["extension"] == ".txt"
        assert meta["title"] == "A Study on Deep Learning"
        assert meta["file_path"] == str(f.resolve())

    def test_md_file(self, tmp_path):
        f = tmp_path / "notes.md"
        f.write_text("# My Research Notes\nSome text here.\n", encoding="utf-8")
        meta = extract_metadata(str(f))
        assert meta["file_name"] == "notes.md"
        assert meta["title"] == "# My Research Notes"

    def test_unknown_extension_fallback_title(self, tmp_path):
        f = tmp_path / "my_research_paper.txt"
        f.write_text("", encoding="utf-8")
        meta = extract_metadata(str(f))
        # Should fall back to stem-based title when text is empty
        assert meta["title"]  # non-empty

    def test_always_has_required_fields(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Some content\n", encoding="utf-8")
        meta = extract_metadata(str(f))
        for field in ("file_path", "file_name", "extension", "title"):
            assert field in meta

    def test_year_extracted_from_text(self, tmp_path):
        f = tmp_path / "paper2019.txt"
        f.write_text("Published in 2019, this study...\n", encoding="utf-8")
        meta = extract_metadata(str(f))
        assert meta.get("year") == 2019
