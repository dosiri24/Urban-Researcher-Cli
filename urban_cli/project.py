from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable


STANDARD_DIRS: Iterable[str] = ("data", "outputs", "logs", "notes")


class ProjectManager:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)

    def create(self, name: str, force: bool = False) -> Path:
        safe = self._safe_name(name)
        root = self.base_dir / safe
        if root.exists() and not force:
            raise FileExistsError(f"이미 존재하는 프로젝트입니다: {root}")
        root.mkdir(parents=True, exist_ok=True)

        for d in STANDARD_DIRS:
            (root / d).mkdir(parents=True, exist_ok=True)

        meta = {
            "id": str(uuid.uuid4()),
            "name": name,
            "safe_name": safe,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "version": 1,
        }
        with (root / "project.json").open("w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return root

    @staticmethod
    def _safe_name(name: str) -> str:
        keep = [c if c.isalnum() or c in ("-", "_") else "-" for c in name.strip()]
        s = "".join(keep)
        while "--" in s:
            s = s.replace("--", "-")
        return s.strip("-") or "project"

    # ----- status helpers -----
    def status(self, root: Path) -> dict:
        root = Path(root)
        meta = self._load_meta(root)
        dirs = {d: (root / d).is_dir() for d in STANDARD_DIRS}
        missing = [d for d, ok in dirs.items() if not ok]
        ok = meta is not None and not missing
        return {
            "root": str(root),
            "ok": ok,
            "meta": meta,
            "dirs": dirs,
            "missing": missing,
        }

    @staticmethod
    def _load_meta(root: Path) -> dict | None:
        pj = Path(root) / "project.json"
        if not pj.exists():
            return None
        try:
            import json

            with pj.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
