"""Tests for the file scanner."""

import os
import tempfile
from pathlib import Path

import pytest

from src.scanner import scan_directory, SUPPORTED_EXTENSIONS


def _make_files(directory: Path, names: list) -> list:
    paths = []
    for name in names:
        p = directory / name
        p.write_text("dummy")
        paths.append(str(p))
    return sorted(paths)


class TestScanDirectory:
    def test_finds_supported_files(self, tmp_path):
        _make_files(tmp_path, ["paper.pdf", "notes.docx", "readme.txt", "article.md"])
        found = scan_directory(str(tmp_path))
        assert len(found) == 4
        assert all(Path(f).suffix.lower() in SUPPORTED_EXTENSIONS for f in found)

    def test_ignores_unsupported_files(self, tmp_path):
        _make_files(tmp_path, ["image.png", "data.csv", "script.py", "paper.pdf"])
        found = scan_directory(str(tmp_path))
        assert len(found) == 1
        assert found[0].endswith("paper.pdf")

    def test_recursive_scan(self, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        (tmp_path / "a.pdf").write_text("x")
        (sub / "b.pdf").write_text("x")
        found = scan_directory(str(tmp_path))
        assert len(found) == 2

    def test_empty_directory(self, tmp_path):
        found = scan_directory(str(tmp_path))
        assert found == []

    def test_returns_sorted_paths(self, tmp_path):
        _make_files(tmp_path, ["z.pdf", "a.pdf", "m.docx"])
        found = scan_directory(str(tmp_path))
        assert found == sorted(found)

    def test_nonexistent_directory_raises(self):
        with pytest.raises(FileNotFoundError):
            scan_directory("/nonexistent/path/that/does/not/exist")

    def test_file_path_raises(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("x")
        with pytest.raises(NotADirectoryError):
            scan_directory(str(f))

    def test_case_insensitive_extensions(self, tmp_path):
        _make_files(tmp_path, ["Paper.PDF", "Notes.DOCX"])
        found = scan_directory(str(tmp_path))
        assert len(found) == 2
