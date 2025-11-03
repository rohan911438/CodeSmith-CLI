from fastapi import FastAPI, Request
from pydantic import BaseModel
from pathlib import Path
from collections import Counter
from core.workbench import scan_repo

app = FastAPI()


class ChatRequest(BaseModel):
    prompt: str
    agent: str | None = None


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

    # Natural repo summary on "explain" prompts for demo-friendly UX
    lower = (prompt or "").strip().lower()
    if any(k in lower for k in ("explain", "what are the files", "list files", "show files")):
        root = Path.cwd()
        files = scan_repo(root)
        total = len(files)
        by_ext = Counter([p.suffix or "<no-ext>" for p in files]).most_common(10)
        top_dirs = Counter([(p.relative_to(root).parts[0] if len(p.relative_to(root).parts) > 1 else "<root>") for p in files]).most_common(10)
        sample = [str(p.relative_to(root)) for p in files[:10]]
        return {
            "summary": {
                "totalFiles": total,
                "topDirs": dict(top_dirs),
                "byExtension": dict(by_ext),
                "sampleFiles": sample,
            }
        }

    model = "gemini-placeholder"
    response = generate_reply(prompt, model=model)
    return {"response": response}


@app.get("/")
def root():
    return {"status": "ok", "agent": "apitest"}
