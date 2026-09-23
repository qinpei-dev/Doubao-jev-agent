"""Run a complete JEV decision and local skill execution."""

import asyncio

from src.core.decision import DecisionEngine
from src.jev.client import JEVClient
from src.skills import SkillExecutor, create_default_registry


async def main() -> None:
    task = "帮我分析这个招聘岗位"
    registry = create_default_registry()
    decision = await DecisionEngine(JEVClient.from_env()).decide(
        task, [skill.name for skill in registry.list()]
    )
    print(f"用户输入：{task}")
    print(f"JEV: {decision.decision} ({decision.confidence:.2%})")
    execution = SkillExecutor(registry).execute(decision, task)
    print(f"Executor: {execution['skill']}.execute()")
    print(f"结果: {execution['result']}")


if __name__ == "__main__":
    asyncio.run(main())
