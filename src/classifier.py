"""Classify papers/materials into topic categories.

Supports two modes:
1. Rule-based (no API key required) – uses keyword matching.
2. LLM-based (requires OPENAI_API_KEY env var) – uses GPT for richer understanding.
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Category definitions for rule-based classification
# ---------------------------------------------------------------------------
CATEGORIES: List[Tuple[str, List[str]]] = [
    (
        "Artificial Intelligence & Machine Learning",
        [
            "machine learning", "deep learning", "neural network", "artificial intelligence",
            "reinforcement learning", "natural language processing", "nlp", "computer vision",
            "transformer", "bert", "gpt", "llm", "large language model", "diffusion",
            "generative", "classification", "regression", "clustering", "gradient descent",
            "backpropagation", "convolutional", "lstm", "attention mechanism", "embedding",
        ],
    ),
    (
        "Computer Science & Systems",
        [
            "algorithm", "data structure", "operating system", "compiler", "database",
            "distributed system", "network protocol", "security", "cryptography",
            "software engineering", "programming language", "parallel computing",
            "cloud computing", "microservice", "kubernetes", "docker",
        ],
    ),
    (
        "Mathematics",
        [
            "theorem", "proof", "algebra", "calculus", "topology", "graph theory",
            "number theory", "differential equation", "linear algebra", "probability",
            "statistics", "optimization", "numerical analysis", "combinatorics",
            "functional analysis", "measure theory",
        ],
    ),
    (
        "Physics",
        [
            "quantum", "mechanics", "thermodynamics", "electromagnetism", "relativity",
            "particle physics", "condensed matter", "optics", "acoustics", "fluid dynamics",
            "cosmology", "astrophysics", "nuclear", "photon", "electron", "spin",
        ],
    ),
    (
        "Biology & Life Sciences",
        [
            "genome", "protein", "cell", "organism", "evolution", "dna", "rna",
            "neuroscience", "bioinformatics", "ecology", "gene", "mutation",
            "molecular biology", "immunology", "pharmacology", "drug", "cancer",
            "metabolism", "enzyme", "bacteria",
        ],
    ),
    (
        "Chemistry",
        [
            "molecular", "reaction", "synthesis", "organic chemistry", "inorganic",
            "polymer", "catalyst", "spectroscopy", "thermochemistry", "electrochemistry",
            "bond", "molecule", "compound", "solvent", "acid", "base",
        ],
    ),
    (
        "Economics & Finance",
        [
            "economic", "finance", "market", "stock", "investment", "gdp", "inflation",
            "monetary", "fiscal", "supply chain", "game theory", "auction", "portfolio",
            "risk", "volatility", "trading", "cryptocurrency",
        ],
    ),
    (
        "Social Sciences & Humanities",
        [
            "sociology", "psychology", "philosophy", "history", "literature", "linguistics",
            "anthropology", "political science", "education", "ethics", "culture",
            "society", "law", "policy", "governance",
        ],
    ),
    (
        "Engineering",
        [
            "mechanical engineering", "civil engineering", "electrical engineering",
            "control system", "signal processing", "robotics", "sensor", "actuator",
            "material science", "nanotechnology", "semiconductor", "circuit",
            "embedded system", "power system", "renewable energy",
        ],
    ),
]


def _rule_based_classify(text: str) -> Tuple[str, float]:
    """Return (category, confidence) based on keyword frequency matching."""
    text_lower = text.lower()
    scores: Dict[str, int] = {}
    for category, keywords in CATEGORIES:
        count = sum(
            len(re.findall(r"\b" + re.escape(kw) + r"\b", text_lower))
            for kw in keywords
        )
        if count:
            scores[category] = count

    if not scores:
        return "General / Uncategorized", 0.0

    best = max(scores, key=lambda k: scores[k])
    total = sum(scores.values())
    confidence = round(scores[best] / total, 2) if total > 0 else 0.0
    return best, confidence


def _llm_classify(title: str, abstract: str, keywords: List[str]) -> Tuple[str, float, List[str]]:
    """Classify using OpenAI ChatCompletion API.

    Returns (category, confidence, suggested_tags).
    Falls back to rule-based if the API call fails.
    """
    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI()

        category_names = [c[0] for c in CATEGORIES] + ["General / Uncategorized"]
        categories_str = "\n".join(f"- {c}" for c in category_names)

        kw_str = ", ".join(keywords) if keywords else "N/A"
        prompt = (
            f"You are a librarian classifying academic papers.\n\n"
            f"Title: {title}\n"
            f"Abstract: {abstract or 'N/A'}\n"
            f"Keywords: {kw_str}\n\n"
            f"Classify this paper into ONE of these categories:\n{categories_str}\n\n"
            f"Also suggest up to 5 specific tags (comma-separated) that describe this paper.\n\n"
            f"Respond in this exact format:\n"
            f"Category: <category name>\n"
            f"Confidence: <0.0-1.0>\n"
            f"Tags: <tag1, tag2, ...>"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
        )

        text = response.choices[0].message.content or ""
        category = "General / Uncategorized"
        confidence = 0.5
        tags: List[str] = []

        for line in text.splitlines():
            if line.startswith("Category:"):
                category = line.split(":", 1)[1].strip()
            elif line.startswith("Confidence:"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("Tags:"):
                raw = line.split(":", 1)[1].strip()
                tags = [t.strip() for t in raw.split(",") if t.strip()]

        return category, confidence, tags

    except Exception:
        return "", 0.0, []


def classify(
    title: str,
    abstract: str = "",
    keywords: Optional[List[str]] = None,
    first_page_text: str = "",
    use_llm: bool = True,
) -> Dict[str, Any]:
    """Classify a paper into a topic category.

    Args:
        title: Paper title.
        abstract: Paper abstract.
        keywords: List of keywords.
        first_page_text: Text of the first page (used for rule-based fallback).
        use_llm: Whether to attempt LLM-based classification (requires OPENAI_API_KEY).

    Returns:
        Dictionary with: category, confidence, method, tags.
    """
    keywords = keywords or []

    # Try LLM first if requested and API key is available
    if use_llm and os.environ.get("OPENAI_API_KEY"):
        category, confidence, tags = _llm_classify(title, abstract, keywords)
        if category:
            return {
                "category": category,
                "confidence": confidence,
                "method": "llm",
                "tags": tags,
            }

    # Fall back to rule-based
    corpus = " ".join(filter(None, [title, abstract, " ".join(keywords), first_page_text]))
    category, confidence = _rule_based_classify(corpus)
    return {
        "category": category,
        "confidence": confidence,
        "method": "rule-based",
        "tags": keywords[:5],
    }
