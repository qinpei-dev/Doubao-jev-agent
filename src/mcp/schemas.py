"""Typed inputs and outputs exposed by the MCP tools."""
from pydantic import BaseModel, Field


class JEVDecideInput(BaseModel):
    task: str = Field(min_length=1, description="Task to make a decision about")
    options: list[str] = Field(min_length=1, description="Allowed decision options")


class JEVDecision(BaseModel):
    decision: str
    confidence: float = Field(ge=0, le=1)


class AgentRunInput(BaseModel):
    task: str = Field(min_length=1, description="Task to route and execute")


class AgentRunOutput(BaseModel):
    decision: "AgentRunDecision"
    execution: "AgentExecution"


class AgentRunDecision(BaseModel):
    skill: str
    confidence: float = Field(ge=0, le=1)


class AgentExecution(BaseModel):
    status: str
    result: str
