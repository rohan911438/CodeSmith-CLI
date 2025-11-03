from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

from core.llm_client import LLMClient

from core.agent_manager import AgentManager
from core.registry import Registry
from core.runtime import Runtime

app = typer.Typer()
console = Console()

ROOT = Path.cwd()
REG = Registry()
MANAGER = AgentManager(registry=REG)
RUNTIME = Runtime(registry=REG)

# Load environment variables from .env if present
load_dotenv()


@app.command()
def create(
    name: str = typer.Argument(..., help="Agent name (folder under agents/)") ,
    type: str = typer.Option("api", help="Agent type: api or mcp"),
    desc: str = typer.Option("", help="Short description"),
    model: str = typer.Option("gemini-placeholder", help="Model name or identifier"),
):
    """Create a new agent scaffold under agents/<name>/"""
    typer.echo(f"Creating agent '{name}' (type={type})...")
    MANAGER.create_agent(name=name, agent_type=type, description=desc, model=model)
    typer.secho(f"✓ Agent '{name}' created at agents/{name}/", fg="green")


@app.command("list")
def list_agents():
    """List all locally created agents"""
    agents = REG.list_agents()
    if not agents:
        console.print("No agents found. Create one with `codesmith create agent <name>`", style="yellow")
        raise typer.Exit()

    table = Table(title="Agents")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Model")
    table.add_column("Description")
    table.add_column("Path")

    for a in agents:
        table.add_row(a["name"], a.get("type", "api"), a.get("model", "-"), a.get("description", "-"), a.get("path", "-"))

    console.print(table)


@app.command()
def run(
    name: str = typer.Argument(..., help="Agent name to run"),
    mcp: bool = typer.Option(False, help="Run in MCP mode (if available)"),
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
):
    """Run an agent locally (starts uvicorn subprocess)"""
    agent = REG.get_agent(name)
    if not agent:
        typer.secho(f"Agent '{name}' not found.", fg="red")
        raise typer.Exit(code=1)

    proc = RUNTIME.run_agent(name=name, host=host, port=port)
    if proc:
        typer.secho(f"🚀 Agent '{name}' running at http://{host}:{port}", fg="green")
        typer.secho(f"Process PID: {proc.pid}")


@app.command()
def chat(
    agent: str = typer.Option(..., help="Agent name to chat with"),
    host: str = typer.Option("127.0.0.1", help="Agent host"),
    port: int = typer.Option(8000, help="Agent port"),
):
    """Open a simple REPL chat to the agent's /chat endpoint"""
    url = f"http://{host}:{port}/chat"
    console.print(f"Connecting to [bold]{agent}[/] at [cyan]{url}[/] (send empty line to quit)")

    with httpx.Client(timeout=30.0) as client:
        while True:
            prompt = typer.prompt("You")
            if prompt.strip() == "":
                console.print("Goodbye.")
                break

            # First try the local agent endpoint
            try:
                resp = client.post(url, json={"prompt": prompt, "agent": agent})
                if resp.status_code == 200:
                    data = resp.json()
                    console.print("[bold green]Agent:[/]")
                    console.print(data.get("response") or data)
                    continue
            except Exception:
                pass

            # Fallback: use LLMClient directly (no server required)
            try:
                llm = LLMClient("gemini")
                text = typer.run_async(llm.generate(prompt)) if hasattr(typer, "run_async") else None
                if text is None:
                    # manual asyncio fallback to avoid introducing an event loop here
                    import asyncio
                    text = asyncio.run(llm.generate(prompt))
                console.print("[bold green]Agent (LLM):[/]")
                console.print(text)
            except Exception as e:
                console.print(f"[red]LLM fallback failed:[/] {e}")


@app.command()
def delete(name: str = typer.Argument(..., help="Agent name to delete"), yes: bool = typer.Option(False, "-y", help="Confirm deletion")):
    """Delete an agent and remove it from the registry"""
    if not yes:
        confirm = typer.confirm(f"Delete agent '{name}'? This removes the folder and registry entry.")
        if not confirm:
            raise typer.Exit()

    ok = MANAGER.delete_agent(name)
    if ok:
        typer.secho(f"Deleted agent '{name}'", fg="green")
    else:
        typer.secho(f"Agent '{name}' not found", fg="red")


@app.command()
def compose(agents: str = typer.Option(..., help="Comma-separated agent names to chain"), name: str = typer.Option(..., help="Composed agent name")):
    """Compose multiple agents into a single chained agent"""
    agent_list = [a.strip() for a in agents.split(",") if a.strip()]
    MANAGER.compose_agents(agent_list, composed_name=name)
    typer.secho(f"Composed agent '{name}' created.", fg="green")


def main():
    app(prog_name="codesmith")


if __name__ == "__main__":
    main()
