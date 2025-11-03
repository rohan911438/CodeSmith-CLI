# CodeSmith CLI — The AI Agent Factory

Create, run, and manage your own AI copilots — directly from your terminal. No Docker. No cloud setup. Instant local magic.

Repository: https://github.com/rohan911438/CLI

Team: BROTHERHOOD
- Rohan Kumar (@rohan911438)
- Ritav PaUl

## ✨ What is CodeSmith CLI?

CodeSmith CLI is a developer tool that lets you generate, customize, and run AI agents locally in seconds. It’s “Gemini CLI meets Copilot” — but open, hackable, and infra-free.

You can:
- Scaffold a new AI agent with one command
- Run it locally as a FastAPI app or as an MCP-style JSON-RPC server
- Chat with it from your terminal
- Compose multiple agents into simple chains

## 🚀 Demo in under 60 seconds

Windows (cmd.exe):

```cmd
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt

python main.py create codebuddy --type api --desc "Explains Python code" --model gemini-pro
python main.py run codebuddy
```

In a new terminal:

```cmd
python main.py chat --agent codebuddy
```

You’ve just built and talked to your own Copilot.

## 📦 Features

- Agent generation: `create <name> --type <api|mcp> --desc "..." --model <model>`
- Local execution: `run <name>`
- Chat from terminal: `chat --agent <name>`
- Composable agents: `compose --agents a,b,c --name mychain`
- Registry: Local JSON registry at `.codesmith/registry.json`
- LLM integration: Async Gemini client with graceful fallback

## 🧠 LLM Integration (Gemini)

We ship an async LLM client (`core/llm_client.py`) that calls the official Google Gemini REST API (v1 `generateContent`).

Environment variable required:

- `GEMINI_API_KEY` — your Gemini API key

Set it per shell:

cmd.exe (current session):
```cmd
set GEMINI_API_KEY=YOUR_KEY
```

cmd.exe (persist):
```cmd
setx GEMINI_API_KEY "YOUR_KEY"
```

PowerShell (current session):
```powershell
$env:GEMINI_API_KEY = "YOUR_KEY"
```

The agent templates gracefully fall back to local echo if the key is missing or a network/auth error occurs, so the CLI never crashes.

## 🛠️ Commands (Typer CLI)

All commands run via `python main.py` from the project root.

- Create an agent
   ```cmd
   python main.py create codebuddy --type api --desc "Explains Python code" --model gemini-pro
   ```

- List agents
   ```cmd
   python main.py list
   ```

- Run an agent (FastAPI server on http://127.0.0.1:8000)
   ```cmd
   python main.py run codebuddy
   ```

- Chat with an agent (simple REPL)
   ```cmd
   python main.py chat --agent codebuddy
   ```

- Delete an agent
   ```cmd
   python main.py delete codebuddy
   ```

- Compose agents (simple chain)
   ```cmd
   python main.py compose --agents a,b,c --name mychain
   ```

- LLM utilities
   - Send a quick prompt to Gemini
      ```cmd
      python main.py llm test "Explain recursion in Python" --model gemini-1.5-flash-latest
      ```
   - List available models on your key
      ```cmd
      python main.py llm list-models
      ```

- Dev mode (safe repo-aware edits)
   - Start interactive replace flow with diff preview
      ```cmd
      python main.py dev run
      ```
      You can type an instruction like: replace 'foo' with 'bar'. CodeSmith will scan your repo, show a patch preview for a few files, and ask for confirmation before applying changes.

## 🧪 Testing

We include a minimal endpoint test runner that spins up agents in-process and exercises their HTTP endpoints using FastAPI’s TestClient.

```cmd
python tests\run_endpoint_tests.py
```

Expected output:

```
PASS: test_api_agent
PASS: test_mcp_agent

All endpoint tests passed.
```

## 📁 Project structure

```
main.py                 # Typer CLI entrypoint
core/
   agent_manager.py      # Creates/deletes agents from templates
   registry.py           # JSON registry (.codesmith/registry.json)
   runtime.py            # Run agents (uvicorn) + chat helpers
   llm_client.py         # Async Gemini client (generateContent)
templates/
   api_main.py           # API agent template (/chat, prompt-based)
   mcp_main.py           # Minimal MCP-like template (/rpc)
   requirements.txt      # Base deps copied into each agent
tests/
   run_endpoint_tests.py # Endpoint smoke tests
```

## 🧩 Architecture in brief

- CLI (Typer) orchestrates registry, agent scaffolding, and runtime.
- Agents are FastAPI apps (or MCP-like services) under `agents/<name>/`.
- LLM calls go through `core/llm_client.py` (async, Gemini-first, provider pluggable).
- Everything runs locally; no Docker or external infra required.

## 🗺️ Roadmap

- Per-agent configurable ports + auto port assignment
- Richer compose (DAGs, branches, conditions)
- First-class tools (file ops, web search, code analysis)
- Web dashboard for monitoring agents
- Optional SQLite registry and metadata

## 👥 Team

BROTHERHOOD — Rohan Kumar and Ritav PaUl

## 📝 License

This project is licensed under the MIT License — see [LICENSE](./LICENSE).

Copyright (c) 2025 Rohan Kumar (@rohan911438)

