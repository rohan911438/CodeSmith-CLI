from fastapi import FastAPI, Request
from pathlib import Path
from typing import Any, Dict

from core.workbench import (
    scan_repo,
    compute_replacements,
    preview_replacement_diffs,
    apply_replacements,
)
from core.dev_actions import backup_files as dev_backup_files

app = FastAPI()


@app.post("/rpc")
async def rpc(req: Request):
    payload = await req.json()
    # Very small JSON-RPC-like handler. For production, use a proper JSON-RPC implementation.
    method = payload.get("method")
    params: Dict[str, Any] = payload.get("params", {}) or {}

    # 1) Simple chat echo (baseline)
    if method == "chat":
        prompt = params.get("prompt", "")
        return {"result": {"response": f"[mcp] Echo: {prompt}"}}

    # 2) files.list — list repository files (relative paths)
    if method == "files.list":
        try:
            limit = int(params.get("limit", 100))
        except Exception:
            limit = 100
        root = Path.cwd()
        files = scan_repo(root)
        rels = [str(p.relative_to(root)) for p in files[: max(0, limit)]]
        return {"result": {"count": len(files), "files": rels}}

    # 3) dev.replace — safe replace with dryRun preview or apply
    if method == "dev.replace":
        search = params.get("search")
        replace = params.get("replace")
        dry_run = params.get("dryRun", True)
        diff_limit = int(params.get("diffLimit", 5))
        if not isinstance(search, str) or not isinstance(replace, str):
            return {"error": "missing or invalid params: 'search' and 'replace' must be strings"}
        root = Path.cwd()
        files = scan_repo(root)
        total, per_file = compute_replacements(files, search, replace)
        diffs = preview_replacement_diffs(per_file, search, replace, limit=diff_limit)
        if dry_run:
            return {
                "result": {
                    "dryRun": True,
                    "matches": total,
                    "files": len(per_file),
                    "diffPreview": {str(k): v for k, v in diffs.items()},
                    "hint": "Call again with dryRun=false to apply; a backup will be created.",
                }
            }
        # Apply with backup
        try:
            dev_backup_files(list(per_file.keys()))
        except Exception:
            # non-fatal; continue without blocking the apply
            pass
        changed = apply_replacements(per_file, search, replace)
        return {
            "result": {
                "dryRun": False,
                "applied": True,
                "changedFiles": changed,
                "matches": total,
            }
        }

    return {"error": "unknown method"}


@app.get("/")
def root():
    return {"status": "ok", "mode": "mcp"}
