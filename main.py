#!/usr/bin/env python3
"""CLI entry point for the Paper/Materials Auto-Organization Agent.

Usage examples:
    # Organize papers (with LLM if OPENAI_API_KEY is set, otherwise rule-based)
    python main.py organize /path/to/papers /path/to/output

    # Dry-run: see what would happen without copying files
    python main.py organize /path/to/papers /path/to/output --dry-run

    # Force rule-based mode (no LLM)
    python main.py organize /path/to/papers /path/to/output --no-llm

    # Use the full agentic loop (LLM-driven)
    python main.py organize /path/to/papers /path/to/output --agent-loop
"""

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.agent import run_agent_loop, run_pipeline

console = Console()


@click.group()
def cli() -> None:
    """📚 论文/资料自动整理 Agent — Paper & Materials Auto-Organization Agent"""


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.argument("output_dir", type=click.Path())
@click.option("--dry-run", is_flag=True, default=False, help="Preview without copying files.")
@click.option("--no-llm", is_flag=True, default=False, help="Use rule-based mode only.")
@click.option(
    "--agent-loop",
    is_flag=True,
    default=False,
    help="Use the full LLM-driven agentic loop (requires OPENAI_API_KEY).",
)
def organize(input_dir: str, output_dir: str, dry_run: bool, no_llm: bool, agent_loop: bool) -> None:
    """Organize papers/materials from INPUT_DIR into OUTPUT_DIR.

    \b
    INPUT_DIR   Directory containing papers/materials (PDF, DOCX, TXT, MD).
    OUTPUT_DIR  Root directory for the organized output.
    """
    use_llm = not no_llm
    messages = []

    def log(msg: str) -> None:
        messages.append(msg)

    console.print(
        Panel(
            f"[bold cyan]📂 输入目录:[/] {input_dir}\n"
            f"[bold cyan]📁 输出目录:[/] {output_dir}\n"
            f"[bold cyan]模式:[/] {'dry-run' if dry_run else '正式'} | "
            f"{'规则分类' if no_llm else 'LLM/规则分类'} | "
            f"{'代理循环' if agent_loop else '顺序流程'}",
            title="[bold]论文/资料自动整理 Agent[/bold]",
            expand=False,
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        task = progress.add_task("处理中...", total=None)

        def progress_log(msg: str) -> None:
            progress.update(task, description=msg[:80])
            log(msg)

        try:
            if agent_loop:
                result = run_agent_loop(
                    input_dir, output_dir, dry_run=dry_run, progress_callback=progress_log
                )
            else:
                result = run_pipeline(
                    input_dir,
                    output_dir,
                    dry_run=dry_run,
                    use_llm=use_llm,
                    progress_callback=progress_log,
                )
        except (FileNotFoundError, NotADirectoryError) as exc:
            console.print(f"[red]错误:[/] {exc}")
            sys.exit(1)

    # Summary table
    summary = result["summary"]
    table = Table(title="分类统计", show_header=True, header_style="bold magenta")
    table.add_column("类别", style="cyan")
    table.add_column("文件数", justify="right", style="green")
    for cat, count in sorted(summary["categories"].items(), key=lambda x: -x[1]):
        table.add_row(cat, str(count))
    console.print(table)

    report_paths = result["report_paths"]
    console.print(
        f"\n[green]✅ 整理完成![/] 共处理 [bold]{summary['total']}[/] 个文件。\n"
        f"📄 JSON 报告: [underline]{report_paths['json_path']}[/]\n"
        f"📝 Markdown 报告: [underline]{report_paths['markdown_path']}[/]"
    )


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
def inspect(file_path: str) -> None:
    """Inspect metadata extracted from a single FILE_PATH."""
    from src.classifier import classify
    from src.extractor import extract_metadata

    meta = extract_metadata(file_path)
    classification = classify(
        title=meta.get("title", ""),
        abstract=meta.get("abstract", ""),
        keywords=meta.get("keywords", []),
        first_page_text=meta.get("first_page_text", ""),
    )

    table = Table(title=f"文件信息: {meta['file_name']}", show_header=True, header_style="bold")
    table.add_column("字段", style="cyan")
    table.add_column("值")

    fields = [
        ("文件名", meta.get("file_name", "")),
        ("标题", meta.get("title", "")),
        ("作者", ", ".join(meta.get("authors", []))),
        ("年份", str(meta.get("year", ""))),
        ("关键词", ", ".join(meta.get("keywords", []))),
        ("摘要", (meta.get("abstract", "") or "")[:200] + ("..." if len(meta.get("abstract", "") or "") > 200 else "")),
        ("类别", classification.get("category", "")),
        ("置信度", str(classification.get("confidence", ""))),
        ("分类方法", classification.get("method", "")),
        ("标签", ", ".join(classification.get("tags", []))),
    ]

    for field, value in fields:
        if value:
            table.add_row(field, value)

    console.print(table)


if __name__ == "__main__":
    cli()
