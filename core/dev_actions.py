from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # optional


BACKUP_ROOT = Path.cwd() / ".codesmith" / "backups"


def _now_slug() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def ensure_backup_root() -> Path:
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    return BACKUP_ROOT


def backup_files(files: List[Path]) -> Path:
    root = ensure_backup_root()
    dest = root / _now_slug()
    dest.mkdir(parents=True, exist_ok=True)
    for p in files:
        if p.is_file():
            target = dest / p.relative_to(Path.cwd())
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
    return dest


def add_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def move_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


def edit_json_file(path: Path, changes: List[Dict[str, Any]]) -> None:
    data: Any = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    for ch in changes:
        op = ch.get("op", "set")
        key = ch.get("key")  # dot path
        value = ch.get("value")
        if not key:
            continue
        parts = str(key).split(".")
        cur = data
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                if op == "set":
                    if isinstance(cur, dict):
                        cur[part] = value
                elif op == "delete":
                    if isinstance(cur, dict) and part in cur:
                        del cur[part]
            else:
                if isinstance(cur, dict):
                    cur = cur.setdefault(part, {})
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def edit_yaml_file(path: Path, changes: List[Dict[str, Any]]) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML not installed; cannot edit YAML files.")
    data: Any = {}
    if path.exists():
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            pass
    for ch in changes:
        op = ch.get("op", "set")
        key = ch.get("key")
        value = ch.get("value")
        if not key:
            continue
        parts = str(key).split(".")
        cur = data
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                if op == "set":
                    if isinstance(cur, dict):
                        cur[part] = value
                elif op == "delete":
                    if isinstance(cur, dict) and part in cur:
                        del cur[part]
            else:
                if isinstance(cur, dict):
                    cur = cur.setdefault(part, {})
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
