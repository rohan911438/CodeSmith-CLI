from __future__ import annotations

import json
import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Optional, List

import httpx
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from dotenv import load_dotenv
import re
import difflib

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
from core.dev_actions import (
    add_file as dev_add_file,
    move_file as dev_move_file,
    edit_json_file as dev_edit_json_file,
    edit_yaml_file as dev_edit_yaml_file,
    backup_files as dev_backup_files,
    restore_backup as dev_restore_backup,
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


def _matches_explain_intent(text: str) -> bool:
    """Return True if the prompt intends to 'explain' files/readme, tolerating typos.

    Accepts synonyms and fuzzy matches for the word 'explain'.
    """
    lower = (text or "").strip().lower()
    keys = ("explain", "what are the files", "list files", "show files", "readme")
    if any(k in lower for k in keys):
        return True
    # Fuzzy: token-level similarity to 'explain'
    tokens = [t for t in re.split(r"\W+", lower) if t]
    try:
        if any(difflib.SequenceMatcher(None, t, "explain").ratio() >= 0.8 for t in tokens):
            return True
    except Exception:
        pass
    return False


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
        # Friendly fallback: summarize repository files when user asks to "explain" (typos tolerated).
        lower = prompt.strip().lower()
        if _matches_explain_intent(lower):
            files = scan_repo(ROOT)
            total = len(files)
            from collections import Counter
            exts = Counter([p.suffix or "<no-ext>" for p in files])
            # Determine top-level directories
            top_dirs = Counter([(p.relative_to(ROOT).parts[0] if len(p.relative_to(ROOT).parts) > 1 else "<root>") for p in files])

            # Build pretty tables
            dir_table = Table(title="Top-level dirs", box=box.SIMPLE_HEAVY)
            dir_table.add_column("Dir", style="cyan", no_wrap=True)
            dir_table.add_column("Count", style="magenta", justify="right")
            for name, cnt in top_dirs.most_common(10):
                dir_table.add_row(name, str(cnt))

            ext_table = Table(title="By extension", box=box.SIMPLE_HEAVY)
            ext_table.add_column("Ext", style="cyan", no_wrap=True)
            ext_table.add_column("Count", style="magenta", justify="right")
            for ext, cnt in exts.most_common(10):
                ext_table.add_row(ext, str(cnt))

            # Biggest files by size (top 10)
            try:
                sized = sorted([(p, p.stat().st_size) for p in files], key=lambda x: x[1], reverse=True)[:10]
            except Exception:
                sized = []
            big_table = Table(title="Largest files", box=box.SIMPLE_HEAVY)
            big_table.add_column("Path", style="green")
            big_table.add_column("Size (KB)", style="yellow", justify="right")
            for p, sz in sized:
                rel = p.relative_to(ROOT)
                kb = max(1, sz // 1024) if sz else 0
                big_table.add_row(str(rel), str(kb))

            header = Panel.fit(f"Total files: [bold]{total}[/bold]", title="Repository summary", border_style="bright_blue")
            console.print(header)
            console.print(dir_table)
            console.print(ext_table)
            if sized:
                console.print(big_table)

            # If registry is available, show agents in a table
            try:
                agents = REG.list_agents()
                if agents:
                    agents_table = Table(title="Registered agents", box=box.SIMPLE_HEAVY)
                    agents_table.add_column("Name", style="cyan")
                    agents_table.add_column("Type", style="magenta")
                    agents_table.add_column("Model", style="yellow")
                    agents_table.add_column("Path", style="green")
                    for a in agents:
                        agents_table.add_row(a.get("name","-"), a.get("type","-"), a.get("model","-"), a.get("path","-"))
                    console.print(agents_table)
            except Exception:
                pass

            # Targeted README.md explanation if requested
            if "readme" in lower:
                readme = ROOT / "README.md"
                if readme.exists():
                    try:
                        text = readme.read_text(encoding="utf-8", errors="ignore")
                        lines = text.splitlines()
                        # Extract headings and bullet stats
                        headings = [ln.strip() for ln in lines if ln.strip().startswith("#")]
                        bullets = [ln for ln in lines if ln.strip().startswith(("- ", "* "))]
                        code_fences = sum(1 for ln in lines if ln.strip().startswith("```") ) // 2
                        # Show first heading and key sections
                        sect_table = Table(title="README overview", box=box.SIMPLE_HEAVY)
                        sect_table.add_column("Metric", style="cyan")
                        sect_table.add_column("Value", style="magenta")
                        first_h = headings[0] if headings else "(no title)"
                        sect_table.add_row("Title", first_h.lstrip("# "))
                        sect_table.add_row("Sections", str(len(headings)))
                        sect_table.add_row("Bullets", str(len(bullets)))
                        sect_table.add_row("Code blocks", str(code_fences))
                        console.print(sect_table)

                        # Show first few non-empty lines as a preview
                        preview = [ln for ln in lines if ln.strip()][:12]
                        console.print(Panel("\n".join(preview), title="README.md preview", border_style="bright_black"))
                    except Exception as e:
                        console.print(f"[yellow]Could not parse README.md:[/] {e}")
                else:
                    console.print("[yellow]README.md not found at project root.[/]")

            raise typer.Exit()

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


# ===== Additional Dev Mode Commands: structured edits =====

@dev_app.command("add-file")
def dev_add_file_cmd(
    path: str = typer.Argument(..., help="Path to create (relative to project root)"),
    content: Optional[str] = typer.Option(None, "--content", help="File content; if omitted, you'll be prompted"),
):
    """Create a new file with preview and confirmation."""
    p = ROOT / path
    if p.exists():
        console.print(f"[yellow]File already exists:[/] {p}")
        raise typer.Exit(code=2)
    if content is None:
        console.print("Enter file content, end with an empty line:")
        lines = []
        while True:
            line = typer.prompt("")
            if line == "":
                break
            lines.append(line)
        content = "\n".join(lines) + ("\n" if lines else "")
    console.rule("Preview")
    console.print(f"[cyan]{p}[/]")
    console.print(content or "(empty)")
    if not typer.confirm("Create this file?", default=True):
        console.print("[yellow]Aborted.[/]")
        raise typer.Exit()
    dev_add_file(p, content or "")
    console.print(f"[green]Created:[/] {p}")


@dev_app.command("move-file")
def dev_move_file_cmd(
    src: str = typer.Argument(..., help="Source path"),
    dst: str = typer.Argument(..., help="Destination path"),
    backup: bool = typer.Option(True, "--backup/--no-backup", help="Backup the source before moving"),
):
    src_p = ROOT / src
    dst_p = ROOT / dst
    if not src_p.exists():
        console.print(f"[red]Source not found:[/] {src_p}")
        raise typer.Exit(code=2)
    console.print(f"Move [cyan]{src_p}[/] -> [cyan]{dst_p}[/]")
    if backup:
        bdir = dev_backup_files([src_p])
        console.print(f"Backup saved to: [magenta]{bdir}[/]")
    if not typer.confirm("Proceed with move?", default=True):
        console.print("[yellow]Aborted.[/]")
        raise typer.Exit()
    dev_move_file(src_p, dst_p)
    console.print("[green]Moved.[/]")


@dev_app.command("edit-json")
def dev_edit_json_cmd(
    path: str = typer.Argument(..., help="JSON file to edit"),
    set: List[str] = typer.Option([], "--set", help="key=value (value parsed as JSON if possible)"),
    delete: List[str] = typer.Option([], "--delete", help="key to remove"),
    backup: bool = typer.Option(True, "--backup/--no-backup", help="Backup file before editing"),
):
    p = ROOT / path
    before = p.read_text(encoding="utf-8") if p.exists() else "{}\n"
    changes: list[dict] = []
    for item in (set or []):
        if "=" not in item:
            console.print(f"[yellow]Ignoring malformed --set:{item}[/]")
            continue
        k, v = item.split("=", 1)
        try:
            v_parsed = json.loads(v)
        except Exception:
            v_parsed = v
        changes.append({"op": "set", "key": k, "value": v_parsed})
    for k in (delete or []):
        changes.append({"op": "delete", "key": k})

    # Preview
    tmp_path = p if p.exists() else p
    if backup and p.exists():
        bdir = dev_backup_files([p])
        console.print(f"Backup saved to: [magenta]{bdir}[/]")
    # Apply to a temp data structure for diff preview
    try:
        before_obj = json.loads(before)
    except Exception:
        before_obj = {}
    # simulate
    sim_path = ROOT / ".codesmith" / "_sim.json"
    sim_path.write_text(json.dumps(before_obj, indent=2), encoding="utf-8")
    dev_edit_json_file(sim_path, changes)
    after = sim_path.read_text(encoding="utf-8")
    sim_path.unlink(missing_ok=True)

    import difflib
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=str(p), tofile=f"{p} (after)")
    console.rule("Preview diff")
    console.print("".join(diff) or "(no changes)")
    if not typer.confirm("Apply these changes?", default=True):
        console.print("[yellow]Aborted.[/]")
        raise typer.Exit()
    # Apply for real
    dev_edit_json_file(p, changes)
    console.print("[green]Applied JSON edits.[/]")


@dev_app.command("edit-yaml")
def dev_edit_yaml_cmd(
    path: str = typer.Argument(..., help="YAML file to edit"),
    set: List[str] = typer.Option([], "--set", help="key=value (value parsed as YAML if possible)"),
    delete: List[str] = typer.Option([], "--delete", help="key to remove"),
    backup: bool = typer.Option(True, "--backup/--no-backup", help="Backup file before editing"),
):
    p = ROOT / path
    try:
        import yaml  # type: ignore
    except Exception:
        console.print("[red]PyYAML not installed. Cannot edit YAML files.[/]")
        raise typer.Exit(code=2)
    before = p.read_text(encoding="utf-8") if p.exists() else "{}\n"
    changes: list[dict] = []
    for item in (set or []):
        if "=" not in item:
            console.print(f"[yellow]Ignoring malformed --set:{item}[/]")
            continue
        k, v = item.split("=", 1)
        try:
            v_parsed = yaml.safe_load(v)
        except Exception:
            v_parsed = v
        changes.append({"op": "set", "key": k, "value": v_parsed})
    for k in (delete or []):
        changes.append({"op": "delete", "key": k})

    if backup and p.exists():
        bdir = dev_backup_files([p])
        console.print(f"Backup saved to: [magenta]{bdir}[/]")

    # simulate for diff
    try:
        before_obj = yaml.safe_load(before) or {}
    except Exception:
        before_obj = {}
    sim_path = ROOT / ".codesmith" / "_sim.yaml"
    sim_path.write_text(yaml.safe_dump(before_obj, sort_keys=False), encoding="utf-8")
    dev_edit_yaml_file(sim_path, changes)
    after = sim_path.read_text(encoding="utf-8")
    sim_path.unlink(missing_ok=True)

    import difflib
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=str(p), tofile=f"{p} (after)")
    console.rule("Preview diff")
    console.print("".join(diff) or "(no changes)")
    if not typer.confirm("Apply these changes?", default=True):
        console.print("[yellow]Aborted.[/]")
        raise typer.Exit()
    dev_edit_yaml_file(p, changes)
    console.print("[green]Applied YAML edits.[/]")


@dev_app.command("rollback")
def dev_rollback_cmd(
    backup_dir: str = typer.Argument(..., help="Path to a backup directory under .codesmith/backups"),
):
    bdir = Path(backup_dir)
    if not bdir.is_absolute():
        bdir = ROOT / bdir
    restored = dev_restore_backup(bdir)
    console.print(f"[green]Restored {restored} file(s) from backup:[/] {bdir}")

def main():
    app(prog_name="codesmith")


if __name__ == "__main__":
    main()
