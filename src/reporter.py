"""Generate JSON and Markdown reports of organized papers."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def generate_report(results: List[Dict[str, Any]], output_dir: str) -> Dict[str, str]:
    """Write a JSON data file and a human-readable Markdown report.

    Args:
        results: List of result dicts produced by the agent for each file.
        output_dir: Directory where the reports are written.

    Returns:
        Dictionary with keys ``json_path`` and ``markdown_path``.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out / f"report_{timestamp}.json"
    md_path = out / f"report_{timestamp}.md"

    # --- JSON ---
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- Markdown ---
    total = len(results)
    successful = sum(1 for r in results if r.get("status") in ("copied", "dry_run"))

    # Group by category
    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        cat = r.get("category", "Unknown")
        by_category.setdefault(cat, []).append(r)

    lines = [
        "# 论文/资料整理报告",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"**共处理文件**: {total}  &nbsp; **成功整理**: {successful}",
        "",
        "---",
        "",
    ]

    for cat in sorted(by_category.keys()):
        items = by_category[cat]
        lines.append(f"## {cat}  ({len(items)} 篇)")
        lines.append("")
        lines.append("| 文件名 | 年份 | 置信度 | 方法 |")
        lines.append("| --- | --- | --- | --- |")
        for r in sorted(items, key=lambda x: (x.get("year") or 0), reverse=True):
            fname = Path(r.get("source", "")).name or r.get("file_name", "")
            year = r.get("year", "-")
            conf = r.get("confidence", "-")
            method = r.get("method", "-")
            lines.append(f"| {fname} | {year} | {conf} | {method} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*由论文/资料自动整理 Agent 生成*")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    return {"json_path": str(json_path), "markdown_path": str(md_path)}
