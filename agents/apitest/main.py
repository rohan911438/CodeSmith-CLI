from fastapi import FastAPI, Request
from pydantic import BaseModel
from pathlib import Path
import difflib

from core.workbench import scan_repo, parse_intent, compute_replacements, apply_replacements, preview_replacement_diffs
from core.dev_actions import add_file as dev_add_file, backup_files as dev_backup_files

app = FastAPI()


class ChatRequest(BaseModel):
    prompt: str
    agent: str | None = None
    apply: bool | None = None  # when True, apply inferred changes instead of just previewing


def generate_reply(prompt: str, model: str = "gemini-placeholder") -> str:
    """Placeholder LLM call — replace this with Gemini SDK or another LLM client.

    Example integration:
      - Use Google's Gemini client to send the prompt and return response text.
      - Keep this function async if the SDK requires async.
    """
    # TODO: integrate Gemini here. For now we echo the prompt.
    return f"[{model}] Echo from agent: {prompt}"


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    prompt = body.get("prompt", "")
    apply = bool(body.get("apply", False))

    # Dev flow: try simple deterministic actions first
    # 1) Replace 'a' with 'b'
    plan = parse_intent(prompt)
    if plan:
        root = Path.cwd()
        files = scan_repo(root)
        total, per_file = compute_replacements(files, plan.search, plan.replace)
        diffs = preview_replacement_diffs(per_file, plan.search, plan.replace, limit=5)
        if not apply:
            return {
                "dev": {
                    "action": "replace",
                    "search": plan.search,
                    "replace": plan.replace,
                    "matches": total,
                    "files": len(per_file),
                    "diffPreview": {str(k): v for k, v in diffs.items()},
                    "hint": "Resend with apply=true to apply changes."
                }
            }
        # Backup files before applying replacements
        try:
            dev_backup_files(list(per_file.keys()))
        except Exception:
            pass
        changed = apply_replacements(per_file, plan.search, plan.replace)
        return {
            "result": {
                "applied": True,
                "changedFiles": changed,
                "note": "Applied replacements",
            }
        }

    # 2) Simple heuristic: create a calculator file on requests that mention 'create' and 'calculator'
    if "create" in prompt.lower() and "calculator" in prompt.lower():
        path = Path.cwd() / "new_folder" / "calculator.py"
        content = (
            "import argparse\nimport sys\n\n"
            "def add(a: float, b: float) -> float:\n    return a + b\n\n"
            "def sub(a: float, b: float) -> float:\n    return a - b\n\n"
            "def mul(a: float, b: float) -> float:\n    return a * b\n\n"
            "def div(a: float, b: float) -> float:\n    if b == 0:\n        raise ZeroDivisionError('Cannot divide by zero')\n    return a / b\n\n"
            "def main(argv: list[str] | None = None) -> int:\n"
            "    argv = sys.argv[1:] if argv is None else argv\n"
            "    if not argv:\n"
            "        print('Usage: add|sub|mul|div a b')\n        return 0\n"
            "    cmd, *nums = argv\n"
            "    a, b = map(float, nums[:2])\n"
            "    match cmd:\n"
            "        case 'add': print(add(a,b))\n"
            "        case 'sub': print(sub(a,b))\n"
            "        case 'mul': print(mul(a,b))\n"
            "        case 'div': print(div(a,b))\n"
            "        case _: print('Unknown command')\n    return 0\n\n"
            "if __name__ == '__main__':\n    raise SystemExit(main())\n"
        )
        if not apply:
            preview = content.splitlines()[:20]
            return {
                "dev": {
                    "action": "add-file",
                    "path": str(path),
                    "contentPreview": "\n".join(preview),
                    "hint": "Resend with apply=true to create the file."
                }
            }
        if path.exists():
            return {"result": {"applied": False, "note": f"File already exists: {path}"}}
        dev_add_file(path, content)
        return {"result": {"applied": True, "created": str(path)}}

    # Fallback: echo
    model = "gemini-placeholder"
    response = generate_reply(prompt, model=model)
    return {"response": response}


@app.get("/")
def root():
    return {"status": "ok", "agent": "apitest"}
