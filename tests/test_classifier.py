"""Tests for the topic classifier."""

import pytest

from src.classifier import classify, _rule_based_classify, CATEGORIES


class TestRuleBasedClassify:
    def test_ml_paper(self):
        cat, conf = _rule_based_classify(
            "deep learning neural network transformer attention mechanism gradient descent"
        )
        assert "Artificial Intelligence" in cat or "Machine Learning" in cat
        assert conf > 0

    def test_math_paper(self):
        cat, conf = _rule_based_classify(
            "theorem proof algebra calculus topology linear algebra differential equation"
        )
        assert "Mathematics" in cat

    def test_physics_paper(self):
        cat, conf = _rule_based_classify(
            "quantum mechanics thermodynamics electromagnetism relativity photon"
        )
        assert "Physics" in cat

    def test_biology_paper(self):
        cat, conf = _rule_based_classify(
            "genome protein cell dna evolution molecular biology gene"
        )
        assert "Biology" in cat

    def test_empty_text_returns_uncategorized(self):
        cat, conf = _rule_based_classify("")
        assert cat == "General / Uncategorized"
        assert conf == 0.0

    def test_no_matching_keywords(self):
        cat, conf = _rule_based_classify("the quick brown fox jumps over the lazy dog")
        assert cat == "General / Uncategorized"


class TestClassify:
    def test_returns_required_fields(self):
        result = classify(
            title="Deep Learning for NLP",
            abstract="We propose a neural network for natural language processing.",
            use_llm=False,
        )
        assert "category" in result
        assert "confidence" in result
        assert "method" in result
        assert "tags" in result

    def test_rule_based_method_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = classify(
            title="Quantum Mechanics and Relativity",
            abstract="Study of quantum field theory and special relativity.",
            use_llm=True,
        )
        assert result["method"] == "rule-based"

    def test_no_llm_flag(self):
        result = classify(
            title="Machine Learning",
            abstract="neural networks and deep learning.",
            use_llm=False,
        )
        assert result["method"] == "rule-based"

    def test_keywords_used_as_tags(self):
        kws = ["neural network", "backpropagation"]
        result = classify(
            title="A Study",
            keywords=kws,
            use_llm=False,
        )
        assert isinstance(result["tags"], list)

    def test_confidence_range(self):
        result = classify(
            title="Deep Learning",
            abstract="transformer model for NLP.",
            use_llm=False,
        )
        assert 0.0 <= result["confidence"] <= 1.0

    def test_first_page_text_used(self):
        result = classify(
            title="Unknown Title",
            first_page_text="quantum mechanics thermodynamics photon spin relativity",
            use_llm=False,
        )
        assert "Physics" in result["category"]
