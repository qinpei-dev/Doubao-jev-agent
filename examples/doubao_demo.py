"""Demonstrate mock Doubao skill routing without a JEV API key."""

import asyncio
from src.core.decision import DecisionEngine
from src.core.router import SkillRouter
from src.jev.mock import MockJEVClient
from src.doubao.adapter import DoubaoAdapter


async def main():
    task = "分析这个岗位是否适合我"
    result = await SkillRouter(DecisionEngine(MockJEVClient())).route(task)
    adapter = DoubaoAdapter()
    print("PermitMCP | Career Routing Demo")
    print(f"Task:       {task}\nSelected:   {result.skill}\nConfidence: {result.confidence:.2f}\nAdapter:    {(await adapter.execute_skill(result.skill, task))['status']}")

if __name__ == "__main__": asyncio.run(main())
