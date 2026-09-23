"""Select a skill for a coding task; uses the local mock without JEV_API_KEY."""

import asyncio

from src.core.decision import DecisionEngine
from src.jev.client import JEVClient


async def main() -> None:
    task = "帮我定位 FastAPI 接口错误"
    options = ["career_skill", "coding_skill", "research_skill", "writing_skill"]
    result = await DecisionEngine(JEVClient.from_env()).decide(task, options)
    print(f"Task: {task}\nJEV decision: {result.decision}\nConfidence: {result.confidence:.2%}\nReason: {result.reason}")


if __name__ == "__main__":
    asyncio.run(main())
