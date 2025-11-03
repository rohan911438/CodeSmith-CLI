from fastapi import FastAPI, Request
from pathlib import Path

from core.workbench import scan_repo, parse_intent, compute_replacements, apply_replacements, preview_replacement_diffs
from core.dev_actions import add_file as dev_add_file, backup_files as dev_backup_files

app = FastAPI()


@app.post("/rpc")
async def rpc(req: Request):
    payload = await req.json()
    # Simple JSON-RPC-like handler.
    method = payload.get("method")
    params = payload.get("params", {})
    if method == "chat":
        prompt = params.get("prompt", "")
        # Fallback echo
        return {"result": {"response": f"[mcp] Echo: {prompt}"}}
    if method == "dev":
        prompt = params.get("prompt", "")
        apply = bool(params.get("apply", False))

        # 1) Replace intent
        plan = parse_intent(prompt)
        if plan:
            root = Path.cwd()
            files = scan_repo(root)
            total, per_file = compute_replacements(files, plan.search, plan.replace)
            diffs = preview_replacement_diffs(per_file, plan.search, plan.replace, limit=5)
            if not apply:
                return {
                    "result": {
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
                }
            try:
                dev_backup_files(list(per_file.keys()))
            except Exception:
                pass
            changed = apply_replacements(per_file, plan.search, plan.replace)
            return {"result": {"applied": True, "changedFiles": changed}}

        # 2) Create calculator
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
                preview = "\n".join(content.splitlines()[:20])
                return {"result": {"dev": {"action": "add-file", "path": str(path), "contentPreview": preview, "hint": "Resend with apply=true to create."}}}
            if path.exists():
                return {"result": {"applied": False, "note": f"File exists: {path}"}}
            dev_add_file(path, content)
            return {"result": {"applied": True, "created": str(path)}}

        return {"error": "unknown dev instruction"}
    return {"error": "unknown method"}


@app.get("/")
def root():
    return {"status": "ok", "mode": "mcp"}
