from __future__ import annotations

import re
from dataclasses import dataclass
import difflib
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


DEFAULT_INCLUDE = (
    "**/*.py",
    "**/*.md",
    "**/*.txt",
    "**/*.json",
    "**/*.yaml",
    "**/*.yml",
    "**/*.toml",
)

DEFAULT_EXCLUDE_DIRS = {".git", "__pycache__", ".venv", ".codesmith", "node_modules"}


@dataclass
class ReplacementPlan:
    search: str
    replace: str


def scan_repo(root: Path, includes: Iterable[str] = DEFAULT_INCLUDE) -> List[Path]:
    files: List[Path] = []
    for pattern in includes:
        for p in root.glob(pattern):
            if not p.is_file():
                continue
            if any(part in DEFAULT_EXCLUDE_DIRS for part in p.parts):
                continue
            files.append(p)
    # de-dup while keeping order
    seen = set()
    uniq: List[Path] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


def parse_intent(prompt: str) -> Optional[ReplacementPlan]:
    """Very small heuristic intent parser for 'replace "a" with "b"' instructions."""
    m = re.search(r"replace\s+[\"'](.+?)[\"']\s+with\s+[\"'](.+?)[\"']", prompt, flags=re.IGNORECASE)
    if m:
        return ReplacementPlan(search=m.group(1), replace=m.group(2))
    return None


def compute_replacements(paths: List[Path], search: str, replace: str) -> Tuple[int, Dict[Path, int]]:
    total = 0
    per_file: Dict[Path, int] = {}
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        count = text.count(search)
        if count:
            per_file[p] = count
            total += count
    return total, per_file


def apply_replacements(per_file: Dict[Path, int], search: str, replace: str) -> int:
    changed_files = 0
    for p, _ in per_file.items():
        try:
            text = p.read_text(encoding="utf-8")
            new_text = text.replace(search, replace)
            if new_text != text:
                p.write_text(new_text, encoding="utf-8")
                changed_files += 1
        except Exception:
            continue
    return changed_files


def preview_replacement_diffs(per_file: Dict[Path, int], search: str, replace: str, limit: int = 10) -> Dict[Path, str]:
    """Return unified diffs for up to `limit` files that would change.

    The diff is generated using difflib and limited in number to keep output concise.
    """
    diffs: Dict[Path, str] = {}
    for i, (p, _) in enumerate(per_file.items()):
        if i >= limit:
            break
        try:
            text = p.read_text(encoding="utf-8")
            new_text = text.replace(search, replace)
            if new_text != text:
                diff_lines = difflib.unified_diff(
                    text.splitlines(keepends=True),
                    new_text.splitlines(keepends=True),
                    fromfile=str(p),
                    tofile=f"{p} (after)",
                )
                diffs[p] = "".join(diff_lines)
        except Exception:
            continue
    return diffs
