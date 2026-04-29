"""Tests for the report generator."""

import json
from pathlib import Path

from src.reporter import generate_report


SAMPLE_RESULTS = [
    {
        "file_name": "deep_learning.pdf",
        "source": "/tmp/deep_learning.pdf",
        "destination": "/output/AI/2023/deep_learning.pdf",
        "status": "copied",
        "category": "Artificial Intelligence & Machine Learning",
        "confidence": 0.9,
        "method": "rule-based",
        "tags": ["neural network"],
        "year": 2023,
    },
    {
        "file_name": "quantum.pdf",
        "source": "/tmp/quantum.pdf",
        "destination": "/output/Physics/2021/quantum.pdf",
        "status": "copied",
        "category": "Physics",
        "confidence": 0.8,
        "method": "rule-based",
        "tags": ["quantum"],
        "year": 2021,
    },
]


class TestGenerateReport:
    def test_creates_json_and_markdown(self, tmp_path):
        paths = generate_report(SAMPLE_RESULTS, str(tmp_path))
        assert Path(paths["json_path"]).exists()
        assert Path(paths["markdown_path"]).exists()

    def test_json_content(self, tmp_path):
        paths = generate_report(SAMPLE_RESULTS, str(tmp_path))
        data = json.loads(Path(paths["json_path"]).read_text(encoding="utf-8"))
        assert len(data) == 2
        assert data[0]["file_name"] == "deep_learning.pdf"

    def test_markdown_contains_categories(self, tmp_path):
        paths = generate_report(SAMPLE_RESULTS, str(tmp_path))
        md = Path(paths["markdown_path"]).read_text(encoding="utf-8")
        assert "Physics" in md
        assert "Artificial Intelligence" in md

    def test_markdown_contains_filenames(self, tmp_path):
        paths = generate_report(SAMPLE_RESULTS, str(tmp_path))
        md = Path(paths["markdown_path"]).read_text(encoding="utf-8")
        assert "deep_learning.pdf" in md
        assert "quantum.pdf" in md

    def test_empty_results(self, tmp_path):
        paths = generate_report([], str(tmp_path))
        data = json.loads(Path(paths["json_path"]).read_text(encoding="utf-8"))
        assert data == []

    def test_output_dir_created_if_missing(self, tmp_path):
        out = tmp_path / "new" / "nested" / "dir"
        paths = generate_report(SAMPLE_RESULTS, str(out))
        assert Path(paths["json_path"]).exists()
