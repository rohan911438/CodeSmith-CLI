from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path.cwd()))

from core.agent_manager import AgentManager
from core.registry import Registry


def ensure_clean_agent(mgr: AgentManager, name: str):
    try:
        mgr.delete_agent(name)
    except Exception:
        pass


def test_api_agent():
    reg = Registry()
    mgr = AgentManager(registry=reg)
    name = "apitest"
    ensure_clean_agent(mgr, name)
    mgr.create_agent(name=name, agent_type="api", description="API test", model="gemini-placeholder")

    mod = importlib.import_module(f"agents.{name}.main")
    app = getattr(mod, "app")
    client = TestClient(app)

    r = client.get("/")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "status" in data and data["status"] == "ok"

    r = client.post("/chat", json={"prompt": "Hello"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "response" in data


def test_mcp_agent():
    reg = Registry()
    mgr = AgentManager(registry=reg)
    name = "mcptest"
    ensure_clean_agent(mgr, name)
    mgr.create_agent(name=name, agent_type="mcp", description="MCP test", model="-")

    mod = importlib.import_module(f"agents.{name}.main")
    app = getattr(mod, "app")
    client = TestClient(app)

    r = client.get("/")
    assert r.status_code == 200, r.text

    r = client.post("/rpc", json={"method": "chat", "params": {"prompt": "Hi"}})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "result" in data and "response" in data["result"]


def test_mcp_files_list():
    reg = Registry()
    mgr = AgentManager(registry=reg)
    name = "mcptest"
    ensure_clean_agent(mgr, name)
    mgr.create_agent(name=name, agent_type="mcp", description="MCP files list", model="-")

    mod = importlib.import_module(f"agents.{name}.main")
    app = getattr(mod, "app")
    client = TestClient(app)

    r = client.post("/rpc", json={"method": "files.list", "params": {"limit": 5}})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "result" in data
    result = data["result"]
    assert isinstance(result.get("count"), int)
    assert isinstance(result.get("files"), list)


def test_mcp_dev_replace_dryrun():
    reg = Registry()
    mgr = AgentManager(registry=reg)
    name = "mcptest"
    ensure_clean_agent(mgr, name)
    mgr.create_agent(name=name, agent_type="mcp", description="MCP replace dryrun", model="-")

    mod = importlib.import_module(f"agents.{name}.main")
    app = getattr(mod, "app")
    client = TestClient(app)

    r = client.post(
        "/rpc",
        json={
            "method": "dev.replace",
            "params": {"search": "Echo", "replace": "ECHO", "dryRun": True, "diffLimit": 1},
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "result" in data
    result = data["result"]
    assert result.get("dryRun") is True
    assert isinstance(result.get("matches"), int)


if __name__ == "__main__":
    failures = []
    for fn in (test_api_agent, test_mcp_agent, test_mcp_files_list, test_mcp_dev_replace_dryrun):
        try:
            fn()
            print(f"PASS: {fn.__name__}")
        except Exception as e:
            failures.append((fn.__name__, str(e)))
            print(f"FAIL: {fn.__name__} -> {e}")

    if failures:
        print("\nSome tests failed:")
        for name, err in failures:
            print(f" - {name}: {err}")
        sys.exit(1)
    else:
        print("\nAll endpoint tests passed.")
