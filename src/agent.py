"""Main agent orchestration for paper/materials auto-organization.

The agent runs a pipeline:
  1. Scan input directory for supported files.
  2. Extract metadata from each file.
  3. Classify each file into a topic category.
  4. Organize (copy) files into the output directory structure.
  5. Generate a report.

An optional agentic loop using OpenAI function-calling is also provided
(activated when ``use_llm=True`` and ``OPENAI_API_KEY`` is set).
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional

from src.classifier import classify
from src.extractor import extract_metadata
from src.organizer import organize_file
from src.reporter import generate_report
from src.scanner import scan_directory


# ---------------------------------------------------------------------------
# Tool definitions (also used for OpenAI function calling)
# ---------------------------------------------------------------------------

def _tool_scan(directory: str) -> Dict[str, Any]:
    files = scan_directory(directory)
    return {"files": files, "count": len(files)}


def _tool_extract(file_path: str) -> Dict[str, Any]:
    return extract_metadata(file_path)


def _tool_classify(
    title: str,
    abstract: str = "",
    keywords: Optional[List[str]] = None,
    first_page_text: str = "",
    use_llm: bool = True,
) -> Dict[str, Any]:
    return classify(
        title=title,
        abstract=abstract,
        keywords=keywords or [],
        first_page_text=first_page_text,
        use_llm=use_llm,
    )


def _tool_organize(
    source_path: str,
    output_dir: str,
    category: str,
    year: Optional[int],
    dry_run: bool = False,
) -> Dict[str, Any]:
    return organize_file(source_path, output_dir, category, year, dry_run=dry_run)


def _tool_report(results: List[Dict[str, Any]], output_dir: str) -> Dict[str, str]:
    return generate_report(results, output_dir)


TOOL_MAP: Dict[str, Callable] = {
    "scan_directory": _tool_scan,
    "extract_metadata": _tool_extract,
    "classify": _tool_classify,
    "organize_file": _tool_organize,
    "generate_report": _tool_report,
}

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "scan_directory",
            "description": "Scan a directory and return all supported paper/material file paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Path to the directory to scan."}
                },
                "required": ["directory"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_metadata",
            "description": "Extract metadata (title, authors, year, abstract, keywords) from a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file."}
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "classify",
            "description": "Classify a paper into a topic category based on its metadata.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "abstract": {"type": "string"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                    "first_page_text": {"type": "string"},
                    "use_llm": {"type": "boolean"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "organize_file",
            "description": "Copy a file into the organized output directory structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_path": {"type": "string"},
                    "output_dir": {"type": "string"},
                    "category": {"type": "string"},
                    "year": {"type": "integer"},
                    "dry_run": {"type": "boolean"},
                },
                "required": ["source_path", "output_dir", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": "Generate a JSON and Markdown report of organized papers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "results": {"type": "array", "items": {"type": "object"}},
                    "output_dir": {"type": "string"},
                },
                "required": ["results", "output_dir"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Simple sequential pipeline (no LLM required)
# ---------------------------------------------------------------------------

def run_pipeline(
    input_dir: str,
    output_dir: str,
    dry_run: bool = False,
    use_llm: bool = True,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Run the full paper organization pipeline.

    Args:
        input_dir: Directory containing papers/materials to organize.
        output_dir: Root directory for the organized output.
        dry_run: If True, compute destinations but do not copy files.
        use_llm: Whether to use OpenAI LLM for classification.
        progress_callback: Optional callable(message) for progress updates.

    Returns:
        Dictionary with keys: results (list), report_paths (dict), summary (dict).
    """

    def log(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    log(f"扫描目录: {input_dir}")
    scan_result = _tool_scan(input_dir)
    files = scan_result["files"]
    log(f"找到 {len(files)} 个文件")

    results: List[Dict[str, Any]] = []

    for file_path in files:
        log(f"处理: {file_path}")

        # Extract
        meta = _tool_extract(file_path)

        # Classify
        classification = _tool_classify(
            title=meta.get("title", ""),
            abstract=meta.get("abstract", ""),
            keywords=meta.get("keywords", []),
            first_page_text=meta.get("first_page_text", ""),
            use_llm=use_llm,
        )

        # Organize
        org = _tool_organize(
            source_path=file_path,
            output_dir=output_dir,
            category=classification["category"],
            year=meta.get("year"),
            dry_run=dry_run,
        )

        record: Dict[str, Any] = {
            **{k: v for k, v in meta.items() if k != "first_page_text"},
            **classification,
            **org,
        }
        results.append(record)
        log(f"  → {classification['category']} ({classification['method']}) → {org['destination']}")

    # Report
    report_dir = output_dir if not dry_run else output_dir
    report_paths = _tool_report(results, report_dir)
    log(f"报告已生成: {report_paths['markdown_path']}")

    categories = {}
    for r in results:
        cat = r.get("category", "Unknown")
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "results": results,
        "report_paths": report_paths,
        "summary": {
            "total": len(results),
            "dry_run": dry_run,
            "categories": categories,
        },
    }


# ---------------------------------------------------------------------------
# Agentic loop using OpenAI function calling (optional)
# ---------------------------------------------------------------------------

def run_agent_loop(
    input_dir: str,
    output_dir: str,
    dry_run: bool = False,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Run the organization task as an LLM-driven agentic loop.

    Falls back to ``run_pipeline`` if OpenAI is not available.

    Args:
        input_dir: Directory to organize.
        output_dir: Root output directory.
        dry_run: Whether to skip actual file copies.
        progress_callback: Optional progress logger.

    Returns:
        Same structure as ``run_pipeline``.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        if progress_callback:
            progress_callback("未检测到 OPENAI_API_KEY，使用规则模式运行流程")
        return run_pipeline(
            input_dir, output_dir, dry_run=dry_run, use_llm=False,
            progress_callback=progress_callback,
        )

    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=api_key)
    except ImportError:
        if progress_callback:
            progress_callback("openai 库未安装，使用规则模式")
        return run_pipeline(
            input_dir, output_dir, dry_run=dry_run, use_llm=False,
            progress_callback=progress_callback,
        )

    def log(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    log("启动 LLM 代理循环...")

    system_prompt = (
        "You are a research paper organization assistant. Your task is to organize all papers "
        f"found in '{input_dir}' into '{output_dir}' by topic and year. "
        "Use the provided tools to: scan the directory, extract metadata from each file, "
        "classify it into a topic category, organize the file, and finally generate a report. "
        f"dry_run={dry_run}. Call generate_report at the end with all results."
    )

    messages = [{"role": "user", "content": system_prompt}]
    results: List[Dict[str, Any]] = []
    max_iterations = 200  # safety limit

    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,  # type: ignore[arg-type]
            tools=OPENAI_TOOLS,  # type: ignore[arg-type]
            tool_choice="auto",
        )

        msg = response.choices[0].message
        messages.append(msg.model_dump())  # type: ignore[arg-type]

        if not msg.tool_calls:
            # Agent has finished
            break

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments or "{}")
            log(f"工具调用: {fn_name}({list(fn_args.keys())})")

            tool_fn = TOOL_MAP.get(fn_name)
            if tool_fn is None:
                tool_result: Any = {"error": f"Unknown tool: {fn_name}"}
            else:
                try:
                    tool_result = tool_fn(**fn_args)
                    # Accumulate per-file results when organize_file is called
                    if fn_name == "organize_file" and isinstance(tool_result, dict):
                        results.append(tool_result)
                except Exception as exc:
                    tool_result = {"error": str(exc)}

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result, ensure_ascii=False, default=str),
                }
            )

    report_paths = generate_report(results, output_dir)
    categories: Dict[str, int] = {}
    for r in results:
        cat = r.get("category", "Unknown")
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "results": results,
        "report_paths": report_paths,
        "summary": {"total": len(results), "dry_run": dry_run, "categories": categories},
    }
