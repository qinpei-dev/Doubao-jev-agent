import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from src.jev.client import JEVClient
from src.jev.mock import MockJEVClient
from src.jev.typesafe import TypeSafeJEVClient
from src.mcp.tools import create_mcp_server


def test_mcp_server_registers_expected_tools():
    server = create_mcp_server(MockJEVClient())
    tools = asyncio.run(server.list_tools())
    assert {tool.name for tool in tools} == {
        "jev_decide", "agent_run", "list_skills", "controlled_agent_run", "approve_action"
    }
    assert server.name == "PermitMCP"


def test_mcp_tools_run_in_mock_mode():
    server = create_mcp_server(MockJEVClient())

    async def run_tools():
        decision = await server.call_tool("jev_decide", {
            "task": "用户想分析一个招聘岗位",
            "options": ["career_skill", "coding_skill", "writing_skill"],
        })
        execution = await server.call_tool("agent_run", {"task": "帮我分析这个岗位"})
        skills = await server.call_tool("list_skills", {})
        return decision, execution, skills

    decision, execution, skills = asyncio.run(run_tools())
    decision_result = json.loads(decision[0].text)
    execution_result = json.loads(execution[0].text)
    assert decision_result["decision"] == "career_skill"
    assert decision_result["confidence"] == 0.91
    assert execution_result["decision"]["skill"] == "career_skill"
    assert execution_result["execution"] == {
        "status": "completed",
        "result": "Career analysis workflow executed",
    }
    assert skills[1]["result"] == ["career_skill", "paper_skill", "coding_skill", "research_skill", "writing_skill"]


def test_server_module_exposes_stdio_startup_entrypoint():
    from src.mcp.server import main, mcp

    assert isinstance(mcp, FastMCP)
    assert callable(main)


def test_mcp_server_process_starts():
    root = Path(__file__).resolve().parents[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "src.mcp.server"],
        cwd=root,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        time.sleep(0.5)
        assert process.poll() is None, process.stderr.read().decode("utf-8", errors="replace")
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_no_key_selects_mock_without_calling_real_api(monkeypatch):
    monkeypatch.setattr("src.jev.client.load_dotenv", lambda: None)
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    assert isinstance(JEVClient.from_env(), MockJEVClient)


def test_own_environment_key_selects_direct_typesafe_client(monkeypatch):
    monkeypatch.setattr("src.jev.client.load_dotenv", lambda: None)
    monkeypatch.setenv("JEV_API_KEY", "user_test_key")
    client = JEVClient.from_env()
    assert isinstance(client, TypeSafeJEVClient)
    assert client.api_key == "user_test_key"
    assert client.endpoint == "https://api.typesafe.ai/v1/systemone"
