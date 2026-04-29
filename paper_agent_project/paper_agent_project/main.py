from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from paper_agent.agents import PaperOrganizerAgent
from paper_agent.config import settings

console = Console()


def cmd_ingest(args: argparse.Namespace) -> None:
    agent = PaperOrganizerAgent()
    records = agent.ingest(args.path)
    if not records:
        console.print("[yellow]没有导入任何资料。请检查路径是否存在，或文件类型是否为 PDF/DOCX/TXT/MD。[/yellow]")
        return

    table = Table(title="导入结果")
    table.add_column("文件")
    table.add_column("文本长度", justify="right")
    table.add_column("切片数", justify="right")
    for r in records:
        table.add_row(r.filename, str(r.text_length), str(r.chunk_count))
    console.print(table)
    console.print(f"[green]索引已建立：{settings.storage_dir}[/green]")


def cmd_summarize(args: argparse.Namespace) -> None:
    agent = PaperOrganizerAgent()
    paths = agent.summarize(args.out)
    if not paths:
        console.print("[yellow]没有可总结的资料。请先执行 ingest。[/yellow]")
        return
    console.print("[green]已生成阅读卡片：[/green]")
    for p in paths:
        console.print(f"- {p}")


def cmd_ask(args: argparse.Namespace) -> None:
    agent = PaperOrganizerAgent()
    answer = agent.ask(args.question, top_k=args.top_k)
    console.print(answer)


def cmd_report(args: argparse.Namespace) -> None:
    agent = PaperOrganizerAgent()
    path = agent.report(args.topic, args.out)
    console.print(f"[green]报告已生成：{path}[/green]")


def cmd_status(args: argparse.Namespace) -> None:
    agent = PaperOrganizerAgent()
    s = agent.status()
    table = Table(title="Agent 状态")
    table.add_column("项目")
    table.add_column("值")
    for k, v in s.items():
        table.add_row(str(k), str(v))
    console.print(table)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="paper-agent",
        description="论文 / 资料自动整理 Agent",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="导入资料并建立索引")
    p_ingest.add_argument("path", type=str, help="文件或文件夹路径，例如 data/input")
    p_ingest.set_defaults(func=cmd_ingest)

    p_sum = sub.add_parser("summarize", help="生成阅读卡片")
    p_sum.add_argument("--out", type=Path, default=settings.output_dir / "cards", help="输出目录")
    p_sum.set_defaults(func=cmd_summarize)

    p_ask = sub.add_parser("ask", help="基于资料问答")
    p_ask.add_argument("question", type=str, help="问题")
    p_ask.add_argument("--top-k", type=int, default=settings.top_k, help="检索片段数量")
    p_ask.set_defaults(func=cmd_ask)

    p_report = sub.add_parser("report", help="生成主题综述报告")
    p_report.add_argument("topic", type=str, help="报告主题")
    p_report.add_argument("--out", type=Path, default=None, help="输出 Markdown 文件路径")
    p_report.set_defaults(func=cmd_report)

    p_status = sub.add_parser("status", help="查看知识库状态")
    p_status.set_defaults(func=cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except KeyboardInterrupt:
        console.print("[red]已中断。[/red]")
        return 130
    except Exception as exc:
        console.print(f"[red]运行失败：{exc}[/red]")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
