# 📚 论文/资料自动整理 Agent

> Paper & Materials Auto-Organization Agent — automatically scan, classify, and organize your research papers and study materials into a structured directory.

---

## Features

| Feature | Description |
|---|---|
| 🔍 **File Scanner** | Recursively discovers PDF, DOCX, DOC, TXT, and Markdown files |
| 📄 **Metadata Extractor** | Extracts title, authors, year, abstract, and keywords from files |
| 🏷️ **Topic Classifier** | Rule-based keyword matching (no API key needed) + optional LLM via OpenAI |
| 📁 **File Organizer** | Copies files into `output/{category}/{year}/` hierarchy |
| 📊 **Report Generator** | Creates JSON data file + human-readable Markdown report |
| 🤖 **Agentic Loop** | Optional GPT-driven loop using OpenAI function calling |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Organize papers (rule-based, no API key required)

```bash
python main.py organize /path/to/papers /path/to/output --no-llm
```

### 3. Organize papers (with OpenAI LLM classification)

```bash
export OPENAI_API_KEY=sk-...
python main.py organize /path/to/papers /path/to/output
```

### 4. Dry-run (preview without copying files)

```bash
python main.py organize /path/to/papers /path/to/output --dry-run --no-llm
```

### 5. Use the full agentic loop (LLM-driven)

```bash
export OPENAI_API_KEY=sk-...
python main.py organize /path/to/papers /path/to/output --agent-loop
```

### 6. Inspect a single file

```bash
python main.py inspect /path/to/paper.pdf
```

---

## Output Structure

```
output/
├── Artificial Intelligence & Machine Learning/
│   ├── 2023/
│   │   └── attention_transformer.pdf
│   └── unknown_year/
│       └── survey_ml.pdf
├── Physics/
│   └── 2022/
│       └── quantum_entanglement.pdf
├── Mathematics/
│   └── 1998/
│       └── algebraic_topology.md
└── report_20240101_120000.md
```

---

## Supported File Types

- **PDF** (`.pdf`) — metadata + text extraction via PyMuPDF
- **Word** (`.docx`, `.doc`) — metadata + text via python-docx
- **Text** (`.txt`, `.md`) — plain-text parsing

---

## Topic Categories

The rule-based classifier covers 9 built-in categories:

1. Artificial Intelligence & Machine Learning
2. Computer Science & Systems
3. Mathematics
4. Physics
5. Biology & Life Sciences
6. Chemistry
7. Economics & Finance
8. Social Sciences & Humanities
9. Engineering

Files that don't match any category are placed in `General / Uncategorized`.

---

## Project Structure

```
agent/
├── main.py              # CLI entry point (click)
├── requirements.txt
├── src/
│   ├── agent.py         # Agent orchestration & agentic loop
│   ├── scanner.py       # File discovery
│   ├── extractor.py     # Metadata extraction
│   ├── classifier.py    # Topic classification
│   ├── organizer.py     # File organization
│   └── reporter.py      # Report generation
└── tests/
    ├── test_scanner.py
    ├── test_extractor.py
    ├── test_classifier.py
    ├── test_organizer.py
    └── test_reporter.py
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Optional | Enables LLM-based classification with GPT |
