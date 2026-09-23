"""Demonstrate mock agent routing without a JEV API key."""

import asyncio
from src.core.decision import DecisionEngine
from src.core.router import AgentRouter
from src.jev.mock import MockJEVClient


async def main():
    task = "分析 GitHub issue"
    result = await AgentRouter(DecisionEngine(MockJEVClient())).route(task)
    print("Doubao JEV Agent | Agent Routing Demo")
    print(f"Task:       {task}\nSelected:   {result.agent}\nConfidence: {result.confidence:.2f}\nReason:     {result.reason}")

if __name__ == "__main__": asyncio.run(main())
