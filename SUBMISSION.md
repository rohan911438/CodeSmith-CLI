# CodeSmith CLI — The AI Agent Factory

## Inspiration
Developers love the magic of Copilot-like assistance but hate the setup tax. We wanted a terminal-first, local‑first way to spin up useful AI agents in seconds—no Docker, no cloud wiring, no vendor lock‑in. Inspired by the speed of CLI tools and the flexibility of FastAPI/MCP, CodeSmith CLI makes “build an agent” as simple as scaffolding a project.

## What it does
CodeSmith CLI lets you create, run, and chat with AI agents locally—fast.

- Scaffold agents from templates (FastAPI or MCP-style JSON‑RPC)
- Run agents locally via Uvicorn (http://127.0.0.1:<port>)
- Chat from your terminal (`/chat` endpoint or CLI REPL)
- Compose multiple agents into simple chains
- Manage agents with a lightweight local registry (.codesmith/registry.json)
- Use an async Gemini client with graceful fallback when API keys are missing or offline
- Developer mode with safe, repo‑aware edits (diff previews, backups, JSON/YAML helpers)

## How we built it
- Language & runtime: Python 3 + Typer for the CLI, asyncio for concurrency
- Web stack: FastAPI agents served by Uvicorn, `httpx` for HTTP
- UX: `rich` for tables and colorful output; `dotenv` for simple env setup
- LLM: `core/llm_client.py` integrates Google Gemini’s generateContent API (async), with local echo fallback on errors/missing keys
- Structure: `core/` (registry, runtime, workbench, dev actions), `templates/` for agent blueprints, `agents/` for user-created agents
- Tests: FastAPI TestClient smoke tests (`tests/run_endpoint_tests.py`) to validate API and MCP templates

## Built with
- Python 3
- Typer (CLI)
- FastAPI (agents)
- Uvicorn[standard] (server; includes PyYAML)
- httpx (HTTP client)
- requests and aiohttp (aux HTTP)
- rich (terminal UX)
- python-dotenv (env config)
- Pydantic (data models)
- asyncio (concurrency)
- Google Gemini REST API (generateContent)

## Challenges we ran into
- Making the CLI resilient when `GEMINI_API_KEY` is missing—fallback without crashes
- Managing event loops cleanly inside a Typer CLI during chat/LLM calls
- Cross‑platform ergonomics on Windows (cmd/PowerShell) and port binding
- Keeping templates minimal yet useful (API + MCP) while avoiding hidden magic
- Safe “dev mode” that previews diffs and backs up files before edits (JSON/YAML)
- Subprocess handling for `uvicorn` (start/stop, readable logs, non‑blocking UX)

## Accomplishments that we're proud of
- A true under‑60‑seconds demo: create → run → chat with your own agent
- Local‑first reliability (works even without a network key via graceful fallback)
- Clean Typer UX with colorful tables and simple commands
- Safe developer tooling: backup + diff previews for edits
- A tiny yet practical test runner that verifies both API and MCP agent templates
- Clear docs and examples that make the first run feel effortless

## What we learned
- Developer trust goes up with visible diffs and reversible actions
- Local‑first designs avoid surprising failure modes and speed iteration
- Typer + FastAPI is a productive combo for CLIs that spin up web apps
- MCP vs REST agents trade simplicity for toolability—offering both helps different use cases
- Small ergonomic details (like Windows‑friendly commands and env var helpers) matter a lot

## What's next for CodeSmith CLI — The AI Agent Factory
- Per‑agent configurable ports + automatic port assignment
- Richer compose: DAGs, branching, and conditional flows
- First‑class tools (file ops, web search, code analysis) exposed to agents
- Optional web dashboard for local monitoring and logs
- Optional SQLite registry and richer per‑agent metadata
- More model providers and pluggable LLM backends
- Packaging for `pipx` + one‑line install; VS Code integration
- Security and sandboxing options for file/network operations

---
Repository: https://github.com/rohan911438/CLI
Team: BROTHERHOOD — Rohan Kumar and Ritav PaUl
License: MIT