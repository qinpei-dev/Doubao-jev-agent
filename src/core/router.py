from .decision import DecisionEngine
from .models import RouteResult, AgentRouteResult

SKILLS = ["paper_skill", "career_skill", "coding_skill", "writing_skill", "research_skill"]
AGENTS = ["coding_agent", "writing_agent", "general_agent"]


class SkillRouter:
    def __init__(self, engine: DecisionEngine): self.engine = engine

    async def route(self, task: str) -> RouteResult:
        result = await self.engine.decide(task, SKILLS)
        return RouteResult(skill=result.decision, confidence=result.confidence, reason=result.reason)


class AgentRouter:
    def __init__(self, engine: DecisionEngine): self.engine = engine

    async def route(self, task: str) -> AgentRouteResult:
        result = await self.engine.decide(task, AGENTS)
        return AgentRouteResult(agent=result.decision, confidence=result.confidence, reason=result.reason)
