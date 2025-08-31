from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    model: str
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 40


class LLMClient:
    """Minimal LLM client interface."""

    def send(self, message: str) -> str:  # pragma: no cover - to be implemented by subclasses
        raise NotImplementedError

