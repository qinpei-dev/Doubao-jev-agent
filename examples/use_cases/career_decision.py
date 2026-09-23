"""Select a skill for a career task; uses the local mock without JEV_API_KEY."""

import asyncio

from src.core.decision import DecisionEngine
from src.jev.client import JEVClient


async def main() -> None:
    task = "帮我分析一个 AI 大模型应用开发实习岗位"
    options = ["career_skill", "coding_skill", "research_skill", "writing_skill"]
    result = await DecisionEngine(JEVClient.from_env()).decide(task, options)
    print(f"Task: {task}\nJEV decision: {result.decision}\nConfidence: {result.confidence:.2%}\nReason: {result.reason}")


if __name__ == "__main__":
    asyncio.run(main())
