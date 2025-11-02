from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


class Registry:
    """Simple JSON registry for local agents.

    Stores metadata in .codesmith/registry.json at the workspace root.
    """

    def __init__(self, path: Optional[Path] = None):
        self.base = Path.cwd()
        self.dir = self.base / ".codesmith"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = path or (self.dir / "registry.json")
        if not self.path.exists():
            self._write({"agents": []})

    def _read(self) -> Dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"agents": []}

    def _write(self, data: Dict):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def list_agents(self) -> List[Dict]:
        data = self._read()
        return data.get("agents", [])

    def add_agent(self, meta: Dict) -> None:
        data = self._read()
        agents = data.setdefault("agents", [])
        # prevent dup
        if any(a.get("name") == meta.get("name") for a in agents):
            # replace
            for i, a in enumerate(agents):
                if a.get("name") == meta.get("name"):
                    agents[i] = meta
                    break
        else:
            agents.append(meta)
        self._write(data)

    def get_agent(self, name: str) -> Optional[Dict]:
        for a in self.list_agents():
            if a.get("name") == name:
                return a
        return None

    def remove_agent(self, name: str) -> bool:
        data = self._read()
        agents = data.get("agents", [])
        new = [a for a in agents if a.get("name") != name]
        if len(new) == len(agents):
            return False
        data["agents"] = new
        self._write(data)
        return True
