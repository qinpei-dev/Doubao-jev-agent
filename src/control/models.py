"""Typed models shared by the controlled agent and its tool boundary."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DecisionOutcome(str, Enum):
    ALLOW = "allow"
    REVIEW = "review"
    DENY = "deny"


class PolicyStatus(str, Enum):
    PASS = "pass"
    REVIEW = "review"
    DENY = "deny"


ToolName = Literal["list_files", "read_file", "write_file", "run_safe_command"]
CONTROLLED_TOOL_NAMES = frozenset({"list_files", "read_file", "write_file", "run_safe_command"})
SAFE_COMMANDS = frozenset({"python-version", "git-status", "git-diff-stat"})


class ActionProposal(BaseModel):
    """An immutable, validated description of one proposed tool action."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    tool: ToolName
    arguments: dict[str, Any]
    description: str = Field(min_length=1, max_length=500)
    # This is caller-supplied context only. Policy decisions use system-derived
    # risk_context in PolicyResult instead.
    risk_context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("action_id")
    @classmethod
    def action_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("action_id must not be blank")
        return value

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("description must not be blank")
        return value

    @model_validator(mode="after")
    def validate_tool_arguments(self) -> "ActionProposal":
        args = self.arguments
        schemas: dict[str, tuple[set[str], set[str]]] = {
            "list_files": ({"path"}, set()),
            "read_file": ({"path"}, {"path"}),
            "write_file": ({"path", "content"}, {"path", "content"}),
            "run_safe_command": ({"command"}, {"command"}),
        }
        accepted, required = schemas[self.tool]
        if set(args) - accepted or required - set(args):
            raise ValueError(f"invalid arguments for {self.tool}")
        for key in ("path", "content", "command"):
            if key in args and not isinstance(args[key], str):
                raise ValueError(f"{key} must be a string")
        if "path" in args and not args["path"].strip():
            raise ValueError("path must not be blank")
        return self

    def digest(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


class PolicyResult(BaseModel):
    status: PolicyStatus
    reason: str
    risk_context: dict[str, Any] = Field(default_factory=dict)
    normalized_path: str | None = None


class ControlDecision(BaseModel):
    action_id: str
    proposal_digest: str
    outcome: DecisionOutcome
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason: str
    source: Literal["jev", "policy", "confidence", "caller"]


class ExecutionPermit(BaseModel):
    """A one-use capability bound to a single immutable action proposal."""

    permit_id: str = Field(default_factory=lambda: str(uuid4()))
    action_id: str
    tool: ToolName
    decision: DecisionOutcome
    approved: bool
    approval_source: Literal["jev", "caller"]
    proposal_digest: str
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolResult(BaseModel):
    status: Literal["success"] = "success"
    output: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Observation(BaseModel):
    status: Literal["success", "blocked", "error"]
    output: str = ""
    error: str | None = None


class AgentFinish(BaseModel):
    final_output: str
    status: Literal["completed", "blocked", "failed"] = "completed"


class AgentStep(BaseModel):
    step: int
    proposal: ActionProposal | None = None
    policy_result: PolicyResult | None = None
    decision: ControlDecision | None = None
    permit: ExecutionPermit | None = None
    execution_status: Literal[
        "success", "blocked", "error", "approval_required", "finished"
    ]
    tool_result: ToolResult | None = None
    observation: Observation | None = None
    error: str | None = None
    final_output: str | None = None


class AgentTrace(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    task: str
    status: Literal["completed", "blocked", "approval_required", "failed"]
    steps: list[AgentStep] = Field(default_factory=list)
    final_output: str | None = None
    stop_reason: str | None = None
    pending_action: ActionProposal | None = None
    pending_decision: ControlDecision | None = None

    def public_dict(self) -> dict[str, Any]:
        """Return an adapter-safe trace without file contents used by the planner."""
        data = self.model_dump(mode="json")
        for step in data["steps"]:
            proposal = step.get("proposal")
            if proposal and proposal["tool"] == "write_file":
                proposal["arguments"]["content"] = "[redacted]"
            if proposal and proposal["tool"] == "read_file":
                if step.get("tool_result"):
                    step["tool_result"]["output"] = "[redacted]"
                if step.get("observation"):
                    step["observation"]["output"] = "[redacted]"
        if data["pending_action"] and data["pending_action"]["tool"] == "write_file":
            data["pending_action"]["arguments"]["content"] = "[redacted]"
        return data


class ControlledAgentRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str = Field(min_length=1, max_length=4000)
    max_steps: int = Field(default=5, ge=1, le=20)

    @field_validator("task")
    @classmethod
    def task_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("task must not be blank")
        return value


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
