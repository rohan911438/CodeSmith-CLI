from fastapi import FastAPI, Request

app = FastAPI()


@app.post("/rpc")
async def rpc(req: Request):
    payload = await req.json()
    # Very small JSON-RPC-like handler. For production, use a proper JSON-RPC implementation.
    method = payload.get("method")
    params = payload.get("params", {})
    if method == "chat":
        prompt = params.get("prompt")
        # placeholder response
        return {"result": {"response": f"[mcp] Echo: {prompt}"}}
    return {"error": "unknown method"}


@app.get("/")
def root():
    return {"status": "ok", "mode": "mcp"}
