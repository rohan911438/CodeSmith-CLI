# CodeSmith CLI — The AI Agent Factory

Create, run, and manage local AI agents (copilots) from your terminal.

Quick start

1. Create a virtualenv and install the project requirements:

   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt

2. Run the CLI (use the Python module or run main.py directly):

   python main.py create codebuddy --type api --desc "Explains Python code"
   python main.py run codebuddy
   python main.py chat --agent codebuddy

Features

- Create agents: `create agent <name> --type <api|mcp> --desc "..." --model <model>`
- List agents: `list`
- Run agent: `run <name>`
- Chat: `chat --agent <name>`
- Delete: `delete <name>`
- Compose agents: `compose --agents a,b,c --name composed`

Notes

- Agent scaffolds live under `agents/<name>/`.
- All agent metadata is stored in `.codesmith/registry.json`.
- Templates include placeholder LLM code. Replace `generate_reply` (in `templates/api_main.py`) with your Gemini or preferred LLM client.

Contributing

This is a hackathon-style starter. Small improvements:

- Add Gemini SDK integration in `templates/api_main.py` and update `requirements.txt` accordingly.
- Add port assignment and automatic open in browser.
- Add tests for registry and manager.
