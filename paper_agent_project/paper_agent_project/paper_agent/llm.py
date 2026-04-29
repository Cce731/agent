from __future__ import annotations

import json
from dataclasses import dataclass

import requests

from .config import settings


@dataclass
class LLMResponse:
    text: str
    used_llm: bool


class LLMClient:
    """Minimal OpenAI-compatible Chat Completions client.

    It calls:
        POST {LLM_BASE_URL}/chat/completions

    If env variables are not configured, `chat` returns an empty fallback response.
    """

    def __init__(self) -> None:
        self.base_url = settings.llm_base_url
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.model)

    def chat(self, prompt: str, temperature: float = 0.2) -> LLMResponse:
        if not self.enabled:
            return LLMResponse(text="", used_llm=False)

        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是严谨的科研资料整理助手。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }

        try:
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return LLMResponse(text=text.strip(), used_llm=True)
        except Exception as exc:
            return LLMResponse(text=f"LLM 调用失败：{exc}", used_llm=False)
