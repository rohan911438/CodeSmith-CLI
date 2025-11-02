import asyncio
from core.llm_client import LLMClient

async def main():
    client = LLMClient(provider="gemini")
    try:
        resp = await client.generate("Explain recursion in Python")
        print("LLM response:", resp)
    except Exception as e:
        print("Error:", e)

asyncio.run(main())