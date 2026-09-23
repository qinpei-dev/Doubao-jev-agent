"""Demonstrate mock skill routing without a JEV API key."""

import asyncio
from src.core.decision import DecisionEngine
from src.core.router import SkillRouter
from src.jev.mock import MockJEVClient


async def main():
    result = await SkillRouter(DecisionEngine(MockJEVClient())).route("帮我优化论文格式")
    print("Doubao JEV Agent | Skill Routing Demo")
    print(f"Task:       帮我优化论文格式\nSelected:   {result.skill}\nConfidence: {result.confidence:.2f}\nReason:     {result.reason}")

if __name__ == "__main__": asyncio.run(main())
