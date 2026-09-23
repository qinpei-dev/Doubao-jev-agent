"""Run an agent-routing decision through TypeSafe JEV or the no-key mock."""

import asyncio

from src.core.decision import DecisionEngine
from src.jev.client import JEVClient


async def main() -> None:
    task = "帮我分析这个招聘岗位"
    options = ["career_agent", "coding_agent", "writing_agent"]
    result = await DecisionEngine(JEVClient.from_env()).decide(task, options)
    print(f"Task: {task}")
    print(f"Decision: {result.decision}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Reason: {result.reason}")


if __name__ == "__main__":
    asyncio.run(main())
