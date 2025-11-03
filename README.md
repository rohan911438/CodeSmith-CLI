# CodeSmith CLI — The AI Agent Factory

Create, run, and manage your own AI copilots — directly from your terminal. No Docker. No cloud setup. Instant local magic.

Repository: https://github.com/rohan911438/CLI

Team: BROTHERHOOD
- Rohan Kumar (@rohan911438)
- Ritav PaUl

---

## ✨ What is CodeSmith CLI?

CodeSmith CLI is a developer tool that lets you generate, customize, and run AI agents locally in seconds. It’s “Gemini CLI meets Copilot” — but open, hackable, and infra‑free.

You can:
- Scaffold a new AI agent with one command
- Run it locally as a FastAPI app or as an MCP‑style JSON‑RPC service
- Chat with it from your terminal or via HTTP
- Compose multiple agents into simple chains
- Use a safe dev mode to preview diffs and back up files before edits

Why this matters for Gemini Hack Day
- Local‑first: demo without risky cloud dependencies; graceful echo fallback if keys/network are missing
- Fast iteration: scaffold → run → chat in under a minute
- Extensible: pluggable model providers, simple templates, clean Python

---

## 🚀 TL;DR (60s demo)

Windows (cmd.exe):

```cmd
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt

python main.py create codebuddy --type api --desc "Explains Python code" --model gemini-pro
python main.py run codebuddy --port 8010
```

In a new terminal:

```cmd
python -c "import requests, json; print(json.dumps(requests.post('http://127.0.0.1:8010/chat', json={'prompt':'Hello'}).json(), indent=2))"
```

You’ve just built and talked to your own Copilot.

---

## 🎯 Demo for judges (one screen)

All commands are Windows cmd.exe, run from the project root.

```cmd
# 1) Install deps
python -m pip install -r requirements.txt

# 2) Prove both templates work (fast smoke tests)
python tests\run_endpoint_tests.py

# 3) Start the sample API agent (use a free port)
python main.py run apitest --port 8021

# 4) In a new terminal: show repo summary via the agent
python -c "import requests, json; r=requests.post('http://127.0.0.1:8021/chat', json={'prompt':'explain the files'}); print(json.dumps(r.json(), indent=2))"

# 5) Optional: safe dev mode with pretty diffs/backups
python main.py dev run
# When prompted: replace 'Echo' with 'ECHO'  (shows diff preview, then confirm)
```

Talking points:
- Local‑first: no Docker, works offline (echo fallback when no GEMINI_API_KEY)
- Deterministic dev mode with diff previews and automatic backups
- Both REST and MCP-style agents validated by tests

---

## 🔧 Installation & Setup

Requirements
- Python 3.11+ recommended
- Windows (cmd.exe/PowerShell), macOS, or Linux

Install (Windows cmd.exe)
```cmd
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Optional: set up a Gemini API key
1) Copy `.env.example` to `.env`
2) Paste your key as `GEMINI_API_KEY=...`

Alternatively, per shell:
```cmd
set GEMINI_API_KEY=YOUR_KEY
```

Verify your key (optional)
```cmd
python main.py llm list-models
python main.py llm test "Explain recursion in Python" --model gemini-1.5-flash-latest
```

No key? No problem — agents gracefully fall back to local echo so your demo never crashes.

---

## 🧭 Core concepts

- Agent: a small FastAPI (or MCP-like) service under `agents/<name>/` exposing `/chat` (REST) or `/rpc` (JSON-RPC style)
- Registry: a local JSON file `.codesmith/registry.json` tracking your agents
- Templates: minimal `api_main.py` and `mcp_main.py` blueprints that you can customize
- Runtime: tiny wrapper that starts uvicorn in a subprocess
- Dev mode: repo-aware helpers to preview diffs, back up files, and apply structured edits safely

---

## 🛠️ CLI commands (Typer)

All commands are run via `python main.py` from the project root.

Create an agent
```cmd
python main.py create codebuddy --type api --desc "Explains Python code" --model gemini-pro
```

List agents
```cmd
python main.py list
```

Run an agent (FastAPI server on http://127.0.0.1:8000)
```cmd
python main.py run codebuddy
```

Run on a specific port
```cmd
python main.py run codebuddy --port 8020
```

Chat with an agent (HTTP client fallback built in)
```cmd
python main.py chat --agent codebuddy --port 8020
```

Compose agents (simple chain)
```cmd
python main.py compose --agents a,b,c --name mychain
```

Delete an agent
```cmd
python main.py delete codebuddy
```

Gemini helpers
```cmd
python main.py llm list-models
python main.py llm test "Explain recursion in Python" --model gemini-1.5-flash-latest
```

Dev mode (safe, repo-aware)
```cmd
python main.py dev run
```
Type: `replace 'foo' with 'bar'` and confirm after the diff preview. Backups are stored under `.codesmith/backups/<timestamp>`.

Structured dev commands
```cmd
python main.py dev add-file new_folder\hello.txt --content "Hello world"
python main.py dev move-file new_folder\hello.txt new_folder\notes\hello.txt
python main.py dev edit-json package.json --set name="\"my-app\"" --delete deprecatedField
python main.py dev edit-yaml config.yaml --set app.name="\"codesmith\""
python main.py dev rollback .codesmith\backups\20251103-120215
```

---

## 🧩 Templates & endpoints

API template (`templates/api_main.py`)
- Endpoint: `POST /chat` with `{ "prompt": "..." }`
- Returns `{ "response": "..." }`
- Judge-friendly enhancement: if the prompt includes “explain”, it returns a repo summary JSON

MCP-style template (`templates/mcp_main.py`)
- Endpoint: `POST /rpc` with `{ "method": "chat", "params": { "prompt": "..." } }`
- Returns `{ "result": { "response": "..." } }`

Example cURL
```cmd
curl -s -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"prompt\":\"Hello\"}"
```

---

## 🚢 Deploy

Pick what fits your demo:

- Docker (recommended for portability)
   1) Build
       ```bash
       docker build -t codesmith:latest .
       ```
   2) Run (default agent: apitest)
       ```bash
       docker run -p 8000:8000 -e PORT=8000 -e AGENT_NAME=apitest codesmith:latest
       ```
   3) Open http://127.0.0.1:8000/

- Render / Railway / Heroku-like
   - This repo includes a flexible `Procfile` (select agent via `AGENT_NAME`, defaults to `apitest`):
      ```
      web: sh -c "python -m uvicorn agents.${AGENT_NAME:-apitest}.main:app --host 0.0.0.0 --port $PORT"
      ```
   - Set environment variables:
      - `AGENT_NAME` (optional) e.g., `apitest` or `mcptest`
      - `GEMINI_API_KEY` (optional)
   - On Heroku, `runtime.txt` pins Python (e.g., `python-3.11.9`)
   - Deploy; the platform injects `$PORT` and runs the web process

- Azure App Service (Linux)
   - Runtime: Python 3.11
   - Startup command:
      ```
      python -m pip install -r requirements.txt && python -m uvicorn agents.apitest.main:app --host 0.0.0.0 --port $PORT
      ```
   - App settings: `WEBSITES_PORT=8000`, optionally `GEMINI_API_KEY`
   - Health check: `/`

Notes
- To run a different agent, set `AGENT_NAME=<your_agent>` in Docker or replace `apitest` in the command.
- This is a local‑first project; LLM calls gracefully fall back if `GEMINI_API_KEY` isn’t set.

---

## 🏗️ Architecture overview

```
main.py                  # Typer CLI entrypoint
core/
   agent_manager.py       # scaffolding from templates + registry wiring
   registry.py            # local JSON registry (.codesmith/registry.json)
   runtime.py             # spawn uvicorn subprocess for an agent
   workbench.py           # safe, deterministic repo edits (diff previews)
   dev_actions.py         # add/move/edit JSON/YAML, backups & rollback
   llm_client.py          # async Gemini client with graceful fallback
templates/
   api_main.py, mcp_main.py, requirements.txt
agents/
   <name>/main.py         # generated from a template
tests/
   run_endpoint_tests.py  # smoke tests for both templates
```

Design principles
- Local-first, predictable behavior (no surprise network failures)
- Minimal magic, small readable modules
- Developer trust: visible diffs, backups, and reversibility

---

## 🧪 Testing

Run the included endpoint tests (uses FastAPI’s TestClient):
```cmd
python tests\run_endpoint_tests.py
```
Expected:
```
PASS: test_api_agent
PASS: test_mcp_agent

All endpoint tests passed.
```

---

## 🔐 Security & privacy

- Keys are read from environment variables or `.env`; never hard‑coded
- No keys are written back to disk; `.env.example` is provided for safe setup
- Local-first by default; when a provider call fails, the app returns a benign echo so your session doesn’t crash

---

## 🩺 Troubleshooting

Port already in use
```cmd
python main.py run apitest --port 8021
```

Kill stuck Python servers (Windows):
```cmd
taskkill /IM python.exe /F
```

Missing GEMINI_API_KEY
- LLM helpers (`llm list-models`, `llm test`) will warn; agent endpoints still work via echo fallback

Windows quoting when passing quotes inside commands
- Use doubled quotes or escape sequences as shown in examples

“Could not infer an action” in dev mode
- Try the deterministic form: `replace 'old' with 'new'`

---

## 🗺️ Roadmap (post‑hackathon)

- Per‑agent configurable ports + automatic port assignment
- Richer compose (DAGs, branches, conditional flows)
- First‑class tools (file ops, web search, code analysis)
- Optional web dashboard for monitoring
- Optional SQLite registry and richer metadata
- More model providers and pluggable LLM backends
- `pipx` packaging for a one‑line install

---

## 👥 Team

BROTHERHOOD — Rohan Kumar and Ritav PaUl

---

## 📝 License

This project is licensed under the MIT License — see [LICENSE](./LICENSE).

Copyright (c) 2025 Rohan Kumar (@rohan911438)

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

   - Structured edits (with backup + diff preview)
      - Create a file:
         ```cmd
         python main.py dev add-file new_folder\hello.txt --content "Hello world"
         ```
         If you omit --content, you’ll be prompted and see a preview before creation.

      - Move a file (backs up by default):
         ```cmd
         python main.py dev move-file new_folder\hello.txt new_folder\notes\hello.txt
         ```

      - Edit JSON with key paths:
         ```cmd
         python main.py dev edit-json package.json --set name="\"my-app\"" --set version="\"0.1.0\"" --delete deprecatedField
         ```
         Values for --set are parsed as JSON when possible (so wrap strings in quotes). A unified diff is shown before applying.

      - Edit YAML (requires PyYAML, included via uvicorn[standard]):
         ```cmd
         python main.py dev edit-yaml config.yaml --set app.name="\"codesmith\"" --delete old.setting
         ```

      - Rollback from a backup folder:
         ```cmd
         python main.py dev rollback .codesmith\backups\20251103-120215
         ```

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

