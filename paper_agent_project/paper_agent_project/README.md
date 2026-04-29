# Paper / Material Auto Organizer Agent

一个可运行的“论文 / 资料自动整理 Agent”示例项目。它可以读取 PDF、DOCX、TXT、MD 文件，自动切分文本、建立检索索引、生成论文阅读卡片、回答基于资料的问题，并输出 Markdown 报告。

## 1. 功能

- 扫描并导入 `data/input` 中的论文和资料文件
- 支持 `.pdf`、`.docx`、`.txt`、`.md`
- 自动切分文本并建立 TF-IDF 检索索引
- 生成论文阅读卡片：研究问题、方法、实验、创新点、局限性、可借鉴内容
- 基于资料进行问答，并给出来源片段
- 根据主题生成资料综述报告
- 可接入 OpenAI-compatible Chat Completions API；没有配置模型时也能使用规则式降级模式运行

## 2. 安装

建议 Python 3.10+。

```bash
cd paper_agent_project
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## 3. 配置可选 LLM

复制 `.env.example` 为 `.env`，并根据你的模型服务修改。

```bash
cp .env.example .env
```

如果你有 OpenAI-compatible 接口：

```bash
LLM_BASE_URL=https://api.example.com/v1
LLM_API_KEY=your_api_key
LLM_MODEL=your_model_name
```

如果不配置，程序会使用本地规则式整理，效果没有大模型好，但可以正常跑通流程。

## 4. 使用方法

把论文或资料放到：

```bash
data/input
```

然后执行：

```bash
# 1. 导入资料并建立索引
python main.py ingest data/input

# 2. 生成所有资料的阅读卡片
python main.py summarize --out outputs/cards

# 3. 基于资料问答
python main.py ask "这几篇论文主要解决了什么问题？"

# 4. 生成某个主题的综述报告
python main.py report "GPU 并行计算优化" --out outputs/report.md

# 5. 查看当前知识库状态
python main.py status
```

## 5. 项目结构

```text
paper_agent_project/
├── main.py
├── requirements.txt
├── .env.example
├── paper_agent/
│   ├── agents.py
│   ├── chunker.py
│   ├── config.py
│   ├── llm.py
│   ├── prompts.py
│   ├── readers.py
│   ├── report.py
│   ├── store.py
│   └── utils.py
├── data/
│   └── input/
└── outputs/
```

## 6. 说明

这是一个课程项目 / 简历项目级别的基础版本。后续可以扩展：

- 接入向量数据库，如 Chroma、FAISS、Milvus
- 使用 embedding 模型替换 TF-IDF
- 增加多 Agent 协作，例如检索 Agent、阅读 Agent、对比 Agent、写作 Agent
- 增加 Web UI，例如 Streamlit 或 FastAPI + Vue
- 增加参考文献格式化、BibTeX 管理、表格识别等能力
