import asyncio
from src.core.decision import DecisionEngine
from src.core.router import SkillRouter, AgentRouter
from src.jev.mock import MockJEVClient
from src.doubao.adapter import DoubaoAdapter


def test_paper_skill_route():
    result = asyncio.run(SkillRouter(DecisionEngine(MockJEVClient())).route("帮我修改论文格式"))
    assert result.skill == "paper_skill"
    assert result.confidence >= 0.9


def test_career_skill_route():
    result = asyncio.run(SkillRouter(DecisionEngine(MockJEVClient())).route("分析这个岗位是否适合我"))
    assert result.skill == "career_skill"


def test_coding_skill_route():
    result = asyncio.run(SkillRouter(DecisionEngine(MockJEVClient())).route("分析这个 Python bug"))
    assert result.skill == "coding_skill"


def test_agent_route():
    result = asyncio.run(AgentRouter(DecisionEngine(MockJEVClient())).route("分析 GitHub issue"))
    assert result.agent == "coding_agent"


def test_adapter_contract():
    result = asyncio.run(DoubaoAdapter().execute_skill("paper_skill", "format paper"))
    assert result["status"] == "adapter_stub"
