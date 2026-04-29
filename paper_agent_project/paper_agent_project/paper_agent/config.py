from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    root_dir: Path = Path(__file__).resolve().parents[1]
    data_dir: Path = root_dir / "data"
    storage_dir: Path = root_dir / "data" / "storage"
    output_dir: Path = root_dir / "outputs"

    llm_base_url: str = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
    llm_api_key: str = os.getenv("LLM_API_KEY", "").strip()
    llm_model: str = os.getenv("LLM_MODEL", "").strip()
    llm_timeout: int = int(os.getenv("LLM_TIMEOUT", "60"))

    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1200"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "180"))
    top_k: int = int(os.getenv("TOP_K", "6"))

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_base_url and self.llm_model)


settings = Settings()
