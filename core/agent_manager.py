from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, List

from .registry import Registry


class AgentManager:
    def __init__(self, registry: Registry):
        self.registry = registry
        self.base = Path.cwd()
        self.agents_dir = self.base / "agents"
        self.agents_dir.mkdir(exist_ok=True)
        self.templates_dir = self.base / "templates"

    def create_agent(self, name: str, agent_type: str = "api", description: str = "", model: str = "") -> None:
        agent_path = self.agents_dir / name
        if agent_path.exists():
            raise FileExistsError(f"Agent {name} already exists")
        agent_path.mkdir(parents=True)

        # copy template main
        tpl_file = self.templates_dir / ("api_main.py" if agent_type == "api" else "mcp_main.py")
        if not tpl_file.exists():
            raise FileNotFoundError(f"Template not found: {tpl_file}")

        main_src = tpl_file.read_text(encoding="utf-8")
        main_py = main_src.replace("__AGENT_NAME__", name).replace("__AGENT_MODEL__", model or "gemini-placeholder")
        (agent_path / "main.py").write_text(main_py, encoding="utf-8")

        # config
        config = {"name": name, "type": agent_type, "description": description, "model": model, "path": str(agent_path)}
        (agent_path / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

        # requirements
        tpl_req = self.templates_dir / "requirements.txt"
        if tpl_req.exists():
            (agent_path / "requirements.txt").write_text(tpl_req.read_text(encoding="utf-8"), encoding="utf-8")

        # register
        self.registry.add_agent(config)

    def delete_agent(self, name: str) -> bool:
        agent = self.registry.get_agent(name)
        if not agent:
            return False
        path = Path(agent.get("path"))
        if path.exists():
            shutil.rmtree(path)
        self.registry.remove_agent(name)
        return True

    def compose_agents(self, names: List[str], composed_name: str) -> None:
        # Create a composed agent that sequentially forwards prompts to agents in names
        agent_path = self.agents_dir / composed_name
        if agent_path.exists():
            raise FileExistsError(f"Agent {composed_name} already exists")
        agent_path.mkdir(parents=True)

        # build composed main.py
        parts = []
        for n in names:
            parts.append(f"    resp = await forward_to_agent('{n}', prompt)\n    prompt = resp.get('response', '')\n")

        composed_src = f"""
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

async def forward_to_agent(name: str, prompt: str):
    url = f'http://127.0.0.1:8000/chat'
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={{'prompt': prompt, 'agent': name}})
        return resp.json()

@app.post('/chat')
async def chat(req: Request):
    payload = await req.json()
    prompt = payload.get('prompt', '')
    # chain through agents
{''.join(parts)}
    return {{'response': prompt}}
"""

        (agent_path / "main.py").write_text(composed_src, encoding="utf-8")
        config = {"name": composed_name, "type": "composed", "description": f"Composed of: {', '.join(names)}", "model": "composed", "path": str(agent_path)}
        (agent_path / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
        self.registry.add_agent(config)
