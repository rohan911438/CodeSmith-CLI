"""Async LLM client with provider abstraction (Gemini-ready).

Provides LLMClient which loads API keys from environment variables and
performs async HTTP calls to the configured provider. Designed to fail
gracefully with human-friendly errors using Rich.

Usage example:
    from core.llm_client import LLMClient
    client = LLMClient(provider="gemini")
    text = await client.generate("Explain recursion in Python")

Notes:
- API keys are read from environment variables (e.g. GEMINI_API_KEY). Never hardcode keys.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, Optional

import aiohttp
from aiohttp import ClientError
from rich.console import Console

console = Console()


class LLMClient:
    """Async client for LLM providers.

    Current default provider: "gemini". The class is small and designed to
    support additional providers later by adding mapping entries to
    `_PROVIDERS`.
    """

    _PROVIDERS: Dict[str, Dict[str, Any]] = {
        "gemini": {
            # Google Gemini REST API (public endpoint)
            # POST https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key=API_KEY
            # Body: {"contents":[{"parts":[{"text": "..."}]}]}
            "env": "GEMINI_API_KEY",
            "endpoint_template": "https://generativelanguage.googleapis.com/v1/models/{model}:generateContent",
            "timeout": 30,
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "auth": "query_key",  # api key passed as ?key=...
        }
    }

    def __init__(self, provider: str = "gemini") -> None:
        self.provider = provider
        if provider not in self._PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")
        self.config = self._PROVIDERS[provider]
        self.api_key: Optional[str] = None

    def load_api_key(self) -> str:
        """Load API key from environment based on provider name.

        Raises:
            ValueError: when the expected API key env var is missing.
        """
        env_name = self.config.get("env")
        key = os.environ.get(env_name)
        if not key:
            raise ValueError(
                f"Missing API key. Please set the environment variable {env_name} with your provider key. "
                "For example (Windows cmd): set %s=YOUR_KEY" % env_name
            )
        self.api_key = key
        return key

    async def generate(self, prompt: str, model: str = "gemini-1.5-flash-latest") -> str:
        """Generate text from the LLM asynchronously.

        This method performs an async HTTP request to the provider. It handles
        network and auth errors gracefully and returns a human-readable message
        in case of failure.
        """
        # Ensure API key present
        try:
            if not self.api_key:
                self.load_api_key()
        except ValueError as e:
            # Re-raise so callers may handle; also print friendly message
            console.print(f"[red]LLM client error:[/red] {e}")
            raise

        timeout = self.config.get("timeout", 30)

        headers = dict(self.config.get("headers", {}))

        # Attempt one or more model ids until one succeeds; if all fail, return a graceful fallback.
        candidates = [model]
        if self.provider == "gemini":
            # add a few sensible fallbacks
            norm = self._normalize_model(model)
            candidates = [norm, "gemini-1.5-pro-latest", "gemini-1.5-flash", "gemini-1.0-pro"]

        last_err: Optional[Exception] = None
        for model_name in candidates:
            try:
                # Build request per attempt
                if self.provider == "gemini":
                    template = self.config.get("endpoint_template")
                    url = template.format(model=model_name)
                    params = {"key": self.api_key}
                    json_body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
                else:
                    url = self.config.get("endpoint")
                    params = None
                    json_body = {"model": model_name, "prompt": prompt}

                async with aiohttp.ClientSession() as session:
                    method = self.config.get("method", "POST").upper()
                    if method == "POST":
                        async with session.post(url, params=params, json=json_body, headers=headers, timeout=timeout) as resp:
                            text = await self._handle_response(resp)
                            return text
                    else:
                        async with session.get(url, params=params or json_body, headers=headers, timeout=timeout) as resp:
                            text = await self._handle_response(resp)
                            return text
            except (asyncio.TimeoutError, ClientError, Exception) as e:
                last_err = e
                continue

        # All attempts failed — log and return a friendly fallback instead of crashing the app.
        if last_err:
            console.print(f"[yellow]LLM currently unavailable:[/yellow] {last_err}")
        return f"[llm unavailable] {prompt}"

    async def _handle_response(self, resp: aiohttp.ClientResponse) -> str:
        """Parse provider response and return generated text or raise on errors."""
        status = resp.status
        try:
            data = await resp.json()
        except Exception:
            text = await resp.text()
            raise RuntimeError(f"Invalid JSON response (status={status}): {text}")

        if status >= 400:
            # attempt to extract provider error message
            err = data.get("error") or data.get("message") or str(data)
            raise RuntimeError(f"Provider error (status={status}): {err}")

        # Provider-specific extraction: try common fields
        if isinstance(data, dict):
            # Gemini response shape: candidates[0].content.parts[0].text
            if "candidates" in data and isinstance(data["candidates"], list) and data["candidates"]:
                first = data["candidates"][0]
                content = first.get("content") if isinstance(first, dict) else None
                if isinstance(content, dict):
                    parts = content.get("parts")
                    if isinstance(parts, list) and parts:
                        part0 = parts[0]
                        if isinstance(part0, dict) and "text" in part0:
                            return part0["text"]
            # Fallback for other shapes
            if "text" in data:
                return data["text"]
            if "response" in data:
                return data["response"]

    def _normalize_model(self, model: str) -> str:
        """Map legacy/alias model names to current Gemini model ids compatible with v1beta.

        Examples:
        - gemini-pro -> gemini-1.5-pro
        - gemini-pro-vision -> gemini-1.5-pro
        - text-bison -> gemini-1.5-flash
        """
        m = (model or "").lower()
        aliases = {
            "gemini-pro": "gemini-1.5-pro-latest",
            "gemini-pro-vision": "gemini-1.5-pro-latest",
            "text-bison": "gemini-1.5-flash-latest",
            "text-bison-001": "gemini-1.5-flash-latest",
            "gemini-1.5-flash": "gemini-1.5-flash-latest",
            "gemini-1.5-pro": "gemini-1.5-pro-latest",
        }
        return aliases.get(m, model)

        # Fallback: stringify the payload
        return str(data)


__all__ = ["LLMClient"]
