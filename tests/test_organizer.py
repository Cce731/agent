"""Tests for the file organizer."""

import shutil
from pathlib import Path

import pytest

from src.organizer import organize_file, _sanitize


class TestSanitize:
    def test_normal_name(self):
        assert _sanitize("Machine Learning") == "Machine Learning"

    def test_unsafe_chars_replaced(self):
        result = _sanitize("AI/ML & NLP: 2024")
        assert "/" not in result
        assert ":" not in result

    def test_empty_string_default(self):
        assert _sanitize("") == "Unknown"

    def test_trims_leading_trailing(self):
        result = _sanitize("  AI  ")
        assert result == "AI"


class TestOrganizeFile:
    def test_copies_file(self, tmp_path):
        src = tmp_path / "paper.pdf"
        src.write_text("content")
        out = tmp_path / "output"

        result = organize_file(str(src), str(out), "Machine Learning", 2023)
        assert result["status"] == "copied"
        dest = Path(result["destination"])
        assert dest.exists()
        assert dest.read_text() == "content"

    def test_directory_structure(self, tmp_path):
        src = tmp_path / "paper.pdf"
        src.write_text("x")
        out = tmp_path / "output"

        result = organize_file(str(src), str(out), "Physics", 2021)
        dest = Path(result["destination"])
        # Should be output/Physics/2021/paper.pdf
        assert dest.parent.name == "2021"
        assert "Physics" in str(dest)

    def test_unknown_year(self, tmp_path):
        src = tmp_path / "paper.pdf"
        src.write_text("x")
        out = tmp_path / "output"

        result = organize_file(str(src), str(out), "Mathematics", None)
        dest = Path(result["destination"])
        assert dest.parent.name == "unknown_year"

    def test_dry_run_does_not_copy(self, tmp_path):
        src = tmp_path / "paper.pdf"
        src.write_text("x")
        out = tmp_path / "output"

        result = organize_file(str(src), str(out), "Chemistry", 2020, dry_run=True)
        assert result["status"] == "dry_run"
        # File should NOT be copied
        assert not Path(result["destination"]).exists()

    def test_duplicate_filename_handling(self, tmp_path):
        src1 = tmp_path / "paper.pdf"
        src1.write_text("first")
        src2 = tmp_path / "sub" / "paper.pdf"
        src2.parent.mkdir()
        src2.write_text("second")
        out = tmp_path / "output"

        result1 = organize_file(str(src1), str(out), "AI", 2022)
        result2 = organize_file(str(src2), str(out), "AI", 2022)
        assert Path(result1["destination"]) != Path(result2["destination"])
        assert Path(result2["destination"]).exists()

    def test_source_and_dest_different(self, tmp_path):
        src = tmp_path / "paper.pdf"
        src.write_text("x")
        out = tmp_path / "output"

        result = organize_file(str(src), str(out), "Biology", 2019)
        assert result["source"] != result["destination"]
