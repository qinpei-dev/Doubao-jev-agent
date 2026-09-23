from pydantic import BaseModel, Field


class DecisionRequest(BaseModel):
    task: str = Field(min_length=1, description="Natural language task")
    options: list[str] = Field(min_length=1, description="Allowed decisions")


class DecisionResult(BaseModel):
    decision: str
    confidence: float = Field(ge=0, le=1)
    reason: str


class RouteRequest(BaseModel):
    task: str = Field(min_length=1)


class RouteResult(BaseModel):
    skill: str
    confidence: float
    reason: str


class AgentRouteResult(BaseModel):
    agent: str
    confidence: float
    reason: str
