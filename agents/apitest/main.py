from fastapi import FastAPI, Request
from pydantic import BaseModel

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
    prompt = body.get("prompt")
    model = "gemini-placeholder"
    response = generate_reply(prompt, model=model)
    return {"response": response}


@app.get("/")
def root():
    return {"status": "ok", "agent": "apitest"}
