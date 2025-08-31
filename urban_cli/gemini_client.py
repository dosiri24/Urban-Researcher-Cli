from __future__ import annotations

import os
from typing import Optional

import google.generativeai as genai

from .llm import LLMClient, LLMConfig


class GeminiClient(LLMClient):
    def __init__(self, api_key: str, config: LLMConfig, system_prompt: Optional[str] = None):
        if not api_key:
            raise ValueError("Gemini API Key is required")
        self.config = config
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name=self.config.model,
            system_instruction=system_prompt or "",
            generation_config={
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "top_k": self.config.top_k,
            },
        )
        self._chat = self._model.start_chat(history=[])

    def send(self, message: str) -> str:
        resp = self._chat.send_message(message)
        # Fallback in case .text missing
        if hasattr(resp, "text") and resp.text:
            return resp.text
        try:
            return "\n".join([p.text for p in getattr(resp, "candidates", []) if getattr(p, "text", None)])
        except Exception:
            return str(resp)

