from fastapi import APIRouter, HTTPException
import httpx
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
        try:
            return await engine.decide(body.task, body.options)
        except (ValueError, httpx.HTTPError) as exc:
            raise HTTPException(502, "Decision engine failed or returned an invalid decision") from exc

    @api.post("/route/skill", response_model=RouteResult)
    async def route_skill(body: RouteRequest):
        try:
            return await skills.route(body.task)
        except (ValueError, httpx.HTTPError) as exc:
            raise HTTPException(502, "Decision engine failed or returned an invalid decision") from exc

    @api.post("/route/agent", response_model=AgentRouteResult)
    async def route_agent(body: RouteRequest):
        try:
            return await agents.route(body.task)
        except (ValueError, httpx.HTTPError) as exc:
            raise HTTPException(502, "Decision engine failed or returned an invalid decision") from exc

    @api.post("/api/v1/agent/run", response_model=AgentRunResult)
    async def run_agent(body: AgentRunRequest):
        try:
            decision = await engine.decide(body.task, [skill.name for skill in registry.list()])
            execution = executor.execute(decision, body.task)
        except (ValueError, httpx.HTTPError) as exc:
            raise HTTPException(502, "Decision engine failed or returned an invalid decision") from exc
        return {
            "decision": {"skill": decision.decision, "confidence": decision.confidence},
            "execution": {"status": execution["status"], "result": execution["result"]},
        }

    return api
