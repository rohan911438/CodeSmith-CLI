from __future__ import annotations

import json
import asyncio
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
from core.workbench import (
    scan_repo,
    parse_intent,
    compute_replacements,
    apply_replacements,
    preview_replacement_diffs,
)

app = typer.Typer()
llm_app = typer.Typer(help="LLM utilities")
dev_app = typer.Typer(help="Interactive developer mode (repo-aware)")
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


@llm_app.command("test")
def llm_test(
    prompt: str = typer.Argument(..., help="Prompt text to send to the LLM"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model id, e.g. gemini-1.5-pro-latest"),
):
    """Send a single prompt to the configured LLM and print the response."""
    try:
        client = LLMClient("gemini")
        text = asyncio.run(client.generate(prompt, model=model or "gemini-1.5-flash-latest"))
        console.print("[bold green]LLM response:[/]")
        console.print(text)
    except Exception as e:
        console.print(f"[red]LLM test failed:[/] {e}")


app.add_typer(llm_app, name="llm")


@dev_app.command("run")
def dev_run():
    """Start an interactive terminal session that:
    - asks for your intent (prompt),
    - requests permission to scan the repo,
    - attempts to interpret a 'replace "a" with "b"' instruction,
    - previews the change set and asks for confirmation,
    - applies edits locally.

    This is a deterministic, safe subset of a full AI refactor. It keeps the UX similar
    to Gemini CLI while avoiding accidental destructive changes.
    """
    console.rule("CodeSmith Dev Mode")
    prompt = typer.prompt("Describe what to do (e.g., replace 'foo' with 'bar')")

    allow_scan = typer.confirm("Allow CodeSmith to scan your repository for candidate files?", default=True)
    if not allow_scan:
        console.print("[yellow]Scan aborted by user.[/yellow]")
        raise typer.Exit()

    files = scan_repo(ROOT)
    console.print(f"[cyan]{len(files)}[/cyan] files scanned.")

    plan = parse_intent(prompt)
    if not plan:
        console.print('[yellow]Could not infer an action. Tip: try "replace \'old\' with \'new\'".[/yellow]')
        raise typer.Exit(code=2)

    total, per_file = compute_replacements(files, plan.search, plan.replace)
    if total == 0:
        console.print(f"[yellow]No occurrences of '{plan.search}' found in repo.[/yellow]")
        raise typer.Exit()

    console.print(f"Will replace [bold]{total}[/] occurrence(s) across [bold]{len(per_file)}[/] file(s).")
    # Show diff previews for the first few files to increase confidence
    diffs = preview_replacement_diffs(per_file, plan.search, plan.replace, limit=5)
    if diffs:
        console.print("\n[bold]Patch preview (first few files):[/]\n")
        for p, d in diffs.items():
            console.print(f"[cyan]{p}[/]")
            console.print(d or "(no visible diff)")
            console.print("")

    if not typer.confirm("Apply these changes?", default=False):
        console.print("[yellow]No changes applied.[/yellow]")
        raise typer.Exit()

    changed = apply_replacements(per_file, plan.search, plan.replace)
    console.print(f"[green]Applied changes to {changed} file(s).[/green]")


app.add_typer(dev_app, name="dev")


@llm_app.command("list-models")
def llm_list_models(json_output: bool = typer.Option(False, "--json", help="Output as JSON list")):
    """List available LLM models for the configured provider (Gemini)."""
    try:
        client = LLMClient("gemini")
        models = asyncio.run(client.list_models())
        if json_output:
            typer.echo(json.dumps(models, indent=2))
            return
        if not models:
            console.print("[yellow]No models returned. Ensure GEMINI_API_KEY is set and has access.[/]")
            return
        table = Table(title="Available Models")
        table.add_column("#", justify="right")
        table.add_column("Model ID")
        for i, m in enumerate(models, 1):
            table.add_row(str(i), m)
        console.print(table)
    except Exception as e:
        console.print(f"[red]Failed to list models:[/] {e}")

def main():
    app(prog_name="codesmith")


if __name__ == "__main__":
    main()
