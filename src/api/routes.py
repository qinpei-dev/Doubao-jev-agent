from fastapi import APIRouter, HTTPException
from ..core.models import DecisionRequest, DecisionResult, RouteRequest, RouteResult, AgentRouteResult, AgentRunRequest, AgentRunResult
from ..core.decision import DecisionEngine
from ..core.router import SkillRouter, AgentRouter
from ..skills import SkillExecutor, SkillRegistry, create_default_registry


def build_router(engine: DecisionEngine, registry: SkillRegistry | None = None) -> APIRouter:
    api = APIRouter()
    registry = registry or create_default_registry()
    skills, agents = SkillRouter(engine), AgentRouter(engine)
    executor = SkillExecutor(registry)

    @api.get("/health")
    async def health(): return {"status": "ok"}

    @api.post("/decide", response_model=DecisionResult)
    async def decide(body: DecisionRequest):
        result = await engine.decide(body.task, body.options)
        if result.decision not in body.options:
            raise HTTPException(502, "Decision engine returned an unavailable option")
        return result

    @api.post("/route/skill", response_model=RouteResult)
    async def route_skill(body: RouteRequest): return await skills.route(body.task)

    @api.post("/route/agent", response_model=AgentRouteResult)
    async def route_agent(body: RouteRequest): return await agents.route(body.task)

    @api.post("/api/v1/agent/run", response_model=AgentRunResult)
    async def run_agent(body: AgentRunRequest):
        decision = await engine.decide(body.task, [skill.name for skill in registry.list()])
        try:
            execution = executor.execute(decision, body.task)
        except ValueError as exc:
            raise HTTPException(502, str(exc)) from exc
        return {
            "decision": {"skill": decision.decision, "confidence": decision.confidence},
            "execution": {"status": execution["status"], "result": execution["result"]},
        }

    return api
