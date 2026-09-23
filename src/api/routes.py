from fastapi import APIRouter, HTTPException
from ..core.models import DecisionRequest, DecisionResult, RouteRequest, RouteResult, AgentRouteResult
from ..core.decision import DecisionEngine
from ..core.router import SkillRouter, AgentRouter


def build_router(engine: DecisionEngine) -> APIRouter:
    api = APIRouter()
    skills, agents = SkillRouter(engine), AgentRouter(engine)

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

    return api
