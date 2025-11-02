from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

from .registry import Registry


class Runtime:
    def __init__(self, registry: Registry):
        self.registry = registry
        self.base = Path.cwd()

    def run_agent(self, name: str, host: str = "127.0.0.1", port: int = 8000) -> Optional[subprocess.Popen]:
        agent = self.registry.get_agent(name)
        if not agent:
            return None

        module = f"agents.{name}.main:app"

        cmd = [sys.executable, "-m", "uvicorn", module, "--host", host, "--port", str(port)]

        # Start uvicorn as a subprocess so the CLI remains responsive.
        proc = subprocess.Popen(cmd)
        return proc
