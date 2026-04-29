from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import ensure_dir, safe_filename, write_json


def card_to_markdown(card: dict[str, Any]) -> str:
    workflow = card.get("workflow") or []
    keywords = card.get("keywords") or []
    if isinstance(workflow, str):
        workflow = [workflow]
    if isinstance(keywords, str):
        keywords = [keywords]

    lines = [
        f"# {card.get('title', '未命名资料')}",
        "",
        "## 1. 核心问题",
        str(card.get("core_problem", "未明确提及")),
        "",
        "## 2. 核心方法",
        str(card.get("method", "未明确提及")),
        "",
        "## 3. 技术流程",
    ]
    if workflow:
        lines.extend([f"- {item}" for item in workflow])
    else:
        lines.append("未明确提及")

    lines.extend(
        [
            "",
            "## 4. 实验或案例",
            str(card.get("experiments_or_cases", "未明确提及")),
            "",
            "## 5. 关键结果",
            str(card.get("key_results", "未明确提及")),
            "",
            "## 6. 创新点",
            str(card.get("innovation", "未明确提及")),
            "",
            "## 7. 局限性",
            str(card.get("limitations", "未明确提及")),
            "",
            "## 8. 关键词",
            "、".join(map(str, keywords)) if keywords else "未明确提及",
            "",
            "## 9. 对项目可借鉴内容",
            str(card.get("usable_for_my_project", "未明确提及")),
            "",
        ]
    )
    return "\n".join(lines)


def save_card(card: dict[str, Any], output_dir: Path) -> Path:
    ensure_dir(output_dir)
    title = str(card.get("title") or "reading_card")
    base = safe_filename(title)
    md_path = output_dir / f"{base}.md"
    json_path = output_dir / f"{base}.json"
    md_path.write_text(card_to_markdown(card), encoding="utf-8")
    write_json(json_path, card)
    return md_path


def build_source_context(results: list[Any], max_chars_each: int = 900) -> str:
    parts: list[str] = []
    for i, r in enumerate(results, start=1):
        page = ""
        if getattr(r, "page_start", None):
            page = f"，页码：{r.page_start}"
        parts.append(
            f"[资料片段 {i}] 来源：{r.filename}{page}，相关度：{r.score:.3f}\n"
            f"{r.text[:max_chars_each]}"
        )
    return "\n\n".join(parts)
