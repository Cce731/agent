from __future__ import annotations

from pathlib import Path
from typing import Any

from .chunker import chunks_from_pages
from .config import settings
from .llm import LLMClient
from .prompts import ANSWER_PROMPT, READING_CARD_PROMPT, REPORT_PROMPT
from .readers import iter_files, read_document
from .report import build_source_context, save_card
from .store import DocumentRecord, KnowledgeStore
from .utils import extract_json_object, file_sha256, normalize_space, safe_filename, stable_id, write_json


class ReaderAgent:
    """负责读取 PDF / DOCX / TXT / MD。"""

    def read(self, path: Path):
        return read_document(path)


class IndexAgent:
    """负责切分文本并建立检索索引。"""

    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store

    def ingest_path(self, path: Path) -> list[DocumentRecord]:
        reader = ReaderAgent()
        records: list[DocumentRecord] = []
        for file in iter_files(path):
            doc = reader.read(file)
            if not doc.text.strip():
                continue
            sha = file_sha256(file)
            doc_id = stable_id(f"{doc.path}:{sha}")
            chunks = chunks_from_pages(doc_id, doc.pages, settings.chunk_size, settings.chunk_overlap)
            record = DocumentRecord(
                doc_id=doc_id,
                path=doc.path,
                filename=doc.filename,
                suffix=doc.suffix,
                title=doc.title,
                sha256=sha,
                text_length=len(doc.text),
                chunk_count=len(chunks),
            )
            self.store.upsert_document(record, chunks)
            records.append(record)
        self.store.rebuild_index()
        return records


class SummaryAgent:
    """负责生成单篇资料阅读卡片。"""

    def __init__(self, store: KnowledgeStore, llm: LLMClient) -> None:
        self.store = store
        self.llm = llm

    def summarize_doc(self, doc_id: str) -> dict[str, Any]:
        doc = self.store.documents[doc_id]
        content = self.store.get_doc_chunks(doc_id, limit_chars=18000)
        prompt = READING_CARD_PROMPT.format(title=doc.get("title", ""), content=content)
        resp = self.llm.chat(prompt, temperature=0.1)

        if resp.used_llm:
            parsed = extract_json_object(resp.text)
            if parsed:
                parsed.setdefault("title", doc.get("title", ""))
                parsed["source_file"] = doc.get("filename", "")
                parsed["doc_id"] = doc_id
                parsed["generated_by"] = "llm"
                return parsed

        return self._fallback_card(doc_id, content, error=resp.text if resp.text else "未配置 LLM，使用规则式降级整理")

    def summarize_all(self, output_dir: Path) -> list[Path]:
        output_paths: list[Path] = []
        cards_index: list[dict[str, Any]] = []
        for doc_id in self.store.documents:
            card = self.summarize_doc(doc_id)
            path = save_card(card, output_dir)
            output_paths.append(path)
            cards_index.append(card)
        write_json(output_dir / "cards_index.json", cards_index)
        return output_paths

    def _fallback_card(self, doc_id: str, content: str, error: str) -> dict[str, Any]:
        doc = self.store.documents[doc_id]
        text = normalize_space(content)
        preview = text[:900]
        keywords = self._simple_keywords(text)
        return {
            "title": doc.get("title", "未命名资料"),
            "source_file": doc.get("filename", ""),
            "doc_id": doc_id,
            "core_problem": self._find_sentence(text, ["problem", "challenge", "问题", "挑战", "瓶颈", "目标"]),
            "method": self._find_sentence(text, ["method", "approach", "algorithm", "方法", "模型", "算法", "框架"]),
            "workflow": ["读取资料", "提取文本", "切分片段", "检索相关内容", "生成阅读卡片"],
            "experiments_or_cases": self._find_sentence(text, ["experiment", "evaluation", "实验", "评估", "数据集", "benchmark"]),
            "key_results": self._find_sentence(text, ["result", "performance", "结果", "性能", "提升", "加速"]),
            "innovation": self._find_sentence(text, ["novel", "contribution", "创新", "贡献", "提出"]),
            "limitations": self._find_sentence(text, ["limitation", "future work", "局限", "不足", "未来工作"]),
            "keywords": keywords,
            "usable_for_my_project": f"可先参考该资料的主题和关键内容：{preview}",
            "generated_by": "fallback",
            "note": error,
        }

    @staticmethod
    def _find_sentence(text: str, keywords: list[str]) -> str:
        if not text:
            return "未明确提及"
        sentences = []
        buf = ""
        for ch in text[:6000]:
            buf += ch
            if ch in "。！？.!?\n":
                sentences.append(buf.strip())
                buf = ""
        if buf.strip():
            sentences.append(buf.strip())
        for s in sentences:
            lower = s.lower()
            if any(k.lower() in lower for k in keywords):
                return s[:500]
        return sentences[0][:500] if sentences else "未明确提及"

    @staticmethod
    def _simple_keywords(text: str, top_n: int = 8) -> list[str]:
        candidates = [
            "GPU", "CPU", "并行", "调度", "优化", "算法", "模型", "实验", "性能", "内存",
            "深度学习", "机器学习", "检索", "向量", "Agent", "LLM", "RAG", "数据集",
            "parallel", "performance", "optimization", "memory", "algorithm", "framework",
        ]
        scored = [(text.lower().count(c.lower()), c) for c in candidates]
        scored.sort(reverse=True)
        return [c for count, c in scored if count > 0][:top_n] or ["资料整理", "文本分析"]


class QAAgent:
    """负责资料问答。"""

    def __init__(self, store: KnowledgeStore, llm: LLMClient) -> None:
        self.store = store
        self.llm = llm

    def answer(self, question: str, top_k: int | None = None) -> str:
        results = self.store.search(question, top_k or settings.top_k)
        if not results:
            return "当前知识库中没有检索到相关资料。请先执行 ingest 导入论文或资料。"

        context = build_source_context(results)
        prompt = ANSWER_PROMPT.format(question=question, context=context)
        resp = self.llm.chat(prompt, temperature=0.1)

        if resp.used_llm and not resp.text.startswith("LLM 调用失败"):
            answer = resp.text
        else:
            answer = self._fallback_answer(question, results, resp.text)

        sources = [
            f"- [{i}] {r.filename}" + (f"，第 {r.page_start} 页" if r.page_start else "") + f"，相关度 {r.score:.3f}"
            for i, r in enumerate(results, start=1)
        ]
        return f"{answer}\n\n## 来源片段\n" + "\n".join(sources)

    @staticmethod
    def _fallback_answer(question: str, results: list[Any], error: str) -> str:
        lines = [f"## 问题\n{question}", "", "## 基于资料的初步回答"]
        for i, r in enumerate(results[:5], start=1):
            lines.append(f"{i}. {r.filename}：{r.text[:350]}...")
        if error:
            lines.append(f"\n> 说明：{error}")
        return "\n".join(lines)


class ReportAgent:
    """负责生成主题综述报告。"""

    def __init__(self, store: KnowledgeStore, llm: LLMClient) -> None:
        self.store = store
        self.llm = llm

    def generate(self, topic: str, output_path: Path) -> Path:
        results = self.store.search(topic, top_k=10)
        context = build_source_context(results, max_chars_each=1000)

        cards_text = self._load_cards_summary()
        prompt = REPORT_PROMPT.format(topic=topic, cards=cards_text, context=context)
        resp = self.llm.chat(prompt, temperature=0.2)

        if resp.used_llm and not resp.text.startswith("LLM 调用失败"):
            report = resp.text
        else:
            report = self._fallback_report(topic, results, resp.text)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        return output_path

    def _load_cards_summary(self) -> str:
        card_files = list((settings.output_dir / "cards").glob("*.json"))
        if not card_files:
            return "暂无阅读卡片。"
        parts = []
        for path in card_files[:20]:
            try:
                import json
                data = json.loads(path.read_text(encoding="utf-8"))
                parts.append(
                    f"标题：{data.get('title')}\n"
                    f"问题：{data.get('core_problem')}\n"
                    f"方法：{data.get('method')}\n"
                    f"结果：{data.get('key_results')}\n"
                    f"借鉴：{data.get('usable_for_my_project')}"
                )
            except Exception:
                continue
        return "\n\n".join(parts) if parts else "暂无阅读卡片。"

    @staticmethod
    def _fallback_report(topic: str, results: list[Any], error: str) -> str:
        lines = [
            f"# {topic} 资料整理报告",
            "",
            "## 1. 研究背景",
            "以下内容根据知识库中检索到的资料片段自动整理。由于未配置可用的大模型接口，当前报告为规则式初稿。",
            "",
            "## 2. 相关资料要点",
        ]
        for i, r in enumerate(results, start=1):
            lines.append(f"### 2.{i} {r.filename}")
            lines.append(r.text[:700])
            lines.append("")
        lines.extend(
            [
                "## 3. 对项目的启发",
                "可以基于上述资料继续提取技术路线、实验指标、性能优化方法和可复用模块。",
                "",
                "## 4. 后续工作建议",
                "建议配置 LLM 接口后重新生成报告，以获得更完整的归纳、对比和总结。",
            ]
        )
        if error:
            lines.append(f"\n> 说明：{error}")
        return "\n".join(lines)


class PaperOrganizerAgent:
    """总控 Agent：串联导入、索引、总结、问答和报告生成。"""

    def __init__(self) -> None:
        self.store = KnowledgeStore(settings.storage_dir)
        self.llm = LLMClient()
        self.index_agent = IndexAgent(self.store)
        self.summary_agent = SummaryAgent(self.store, self.llm)
        self.qa_agent = QAAgent(self.store, self.llm)
        self.report_agent = ReportAgent(self.store, self.llm)

    def ingest(self, path: str | Path) -> list[DocumentRecord]:
        return self.index_agent.ingest_path(Path(path))

    def summarize(self, output_dir: str | Path | None = None) -> list[Path]:
        out = Path(output_dir) if output_dir else settings.output_dir / "cards"
        return self.summary_agent.summarize_all(out)

    def ask(self, question: str, top_k: int | None = None) -> str:
        return self.qa_agent.answer(question, top_k=top_k)

    def report(self, topic: str, output_path: str | Path | None = None) -> Path:
        if output_path:
            out = Path(output_path)
        else:
            out = settings.output_dir / f"{safe_filename(topic)}_report.md"
        return self.report_agent.generate(topic, out)

    def status(self) -> dict[str, Any]:
        s = self.store.stats()
        return {
            **s,
            "llm_enabled": self.llm.enabled,
            "storage_dir": str(settings.storage_dir),
            "output_dir": str(settings.output_dir),
        }
