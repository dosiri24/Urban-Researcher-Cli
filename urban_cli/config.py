from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_DIR = Path(os.path.expanduser("~/.urban_researcher"))
DEFAULT_FILE = DEFAULT_DIR / "config.json"


@dataclass
class ConfigManager:
    path: Path = DEFAULT_FILE

    def _ensure_dir(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def _write(self, data: Dict[str, Any]) -> None:
        self._ensure_dir()
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.path)

    def set(self, key: str, value: Any) -> None:
        data = self._read()
        data[key] = value
        self._write(data)

    def get(self, key: str) -> Optional[Any]:
        # ENV 우선
        env_key = self._env_key(key)
        if env_key in os.environ:
            return os.environ[env_key]
        return self._read().get(key)

    def all(self) -> Dict[str, Any]:
        data = self._read()
        # ENV 병합(ENV 우선)
        for k in list(data.keys()):
            env_key = self._env_key(k)
            if env_key in os.environ:
                data[k] = os.environ[env_key]
        return data

    @staticmethod
    def _env_key(key: str) -> str:
        # 예: api-key -> UR_API_KEY
        up = key.upper().replace("-", "_")
        return f"UR_{up}"

    @staticmethod
    def mask(value: str, keep: int = 2) -> str:
        if not value:
            return ""
        if len(value) <= keep * 2:
            return "*" * len(value)
        return value[:keep] + "*" * (len(value) - keep * 2) + value[-keep:]

    def unset(self, key: str) -> bool:
        data = self._read()
        existed = key in data
        if existed:
            del data[key]
            self._write(data)
        return existed
