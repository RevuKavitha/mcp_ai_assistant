from __future__ import annotations

import json
from typing import Any, Dict, List

import httpx


class OpenAIClient:
    """Hosted LLM client using OpenAI-compatible /v1/chat/completions API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for hosted LLM mode")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def generate_json(self, prompt: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        content = await self._chat(payload)
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Hosted LLM returned invalid JSON: {content}") from exc

    async def generate_text(self, prompt: str) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
        }
        return await self._chat(payload)

    async def _chat(self, payload: Dict[str, Any]) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
        return self._extract_text(body).strip()

    @staticmethod
    def _extract_text(body: Dict[str, Any]) -> str:
        choices: List[Dict[str, Any]] = body.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(str(part.get("text", "")))
            return "".join(text_parts)
        return str(content)
