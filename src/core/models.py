from pydantic import BaseModel, Field, field_validator


class DecisionRequest(BaseModel):
    task: str = Field(min_length=1, description="Natural language task")
    options: list[str] = Field(
        min_length=1,
        max_length=255,
        description="Allowed decisions (TypeSafe Choice supports up to 255 options)",
    )

    @field_validator("task")
    @classmethod
    def task_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("task must not be empty")
        return value

    @field_validator("options")
    @classmethod
    def options_must_be_non_blank_and_unique(cls, value: list[str]) -> list[str]:
        if any(not option.strip() for option in value):
            raise ValueError("options must contain non-empty choices")
        if len(value) != len(set(value)):
            raise ValueError("options must not contain duplicates")
        return value


class DecisionResult(BaseModel):
    decision: str
    confidence: float = Field(ge=0, le=1)
    reason: str


class RouteRequest(BaseModel):
    task: str = Field(min_length=1)

    @field_validator("task")
    @classmethod
    def task_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("task must not be empty")
        return value


class RouteResult(BaseModel):
    skill: str
    confidence: float = Field(ge=0, le=1)
    reason: str


class AgentRouteResult(BaseModel):
    agent: str
    confidence: float = Field(ge=0, le=1)
    reason: str


class AgentRunRequest(BaseModel):
    task: str = Field(min_length=1)

    @field_validator("task")
    @classmethod
    def task_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("task must not be empty")
        return value


class AgentRunDecision(BaseModel):
    skill: str
    confidence: float = Field(ge=0, le=1)


class AgentRunExecution(BaseModel):
    status: str
    result: str


class AgentRunResult(BaseModel):
    decision: AgentRunDecision
    execution: AgentRunExecution
