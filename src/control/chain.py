"""One proposal through policy, optional decision, permit, and execution."""

from dataclasses import dataclass
from typing import Literal, Protocol

from .controller import DecisionController
from .errors import PolicyDenied, ReviewRequired
from .models import (
    ActionProposal, ControlDecision, DecisionOutcome, ExecutionPermit,
    PolicyResult, PolicyStatus, ToolResult,
)
from .permits import ExecutionPermitAuthority


class ToolExecutor(Protocol):
    def execute(self, proposal: ActionProposal, permit: ExecutionPermit) -> ToolResult: ...


@dataclass
class ControlResult:
    status: Literal["success", "blocked", "review", "error"]
    policy_result: PolicyResult
    decision: ControlDecision
    permit: ExecutionPermit | None = None
    tool_result: ToolResult | None = None
    error: str | None = None


class ControlChain:
    """Per-call control with no planner, history, or registered tool assumptions."""

    def __init__(self, controller: DecisionController, permits: ExecutionPermitAuthority, executor: ToolExecutor):
        self.controller = controller
        self.policy = controller.policy
        self.permits = permits
        self.executor = executor

    async def run(self, proposal: ActionProposal) -> ControlResult:
        policy, decision = await self.controller.decide(proposal)
        if decision.action_id != proposal.action_id or decision.proposal_digest != proposal.digest():
            raise ValueError("control decision is not bound to this proposal")
        if decision.outcome == DecisionOutcome.DENY:
            return ControlResult("blocked", policy, decision)
        if decision.outcome == DecisionOutcome.REVIEW:
            return ControlResult("review", policy, decision)
        return self._execute(proposal, policy, decision, decision.source)

    def approve(self, proposal: ActionProposal, reviewed: ControlResult) -> ControlResult:
        if reviewed.status != "review" or reviewed.decision.outcome != DecisionOutcome.REVIEW:
            raise ValueError("only a reviewed action can be approved")
        if reviewed.decision.action_id != proposal.action_id or reviewed.decision.proposal_digest != proposal.digest():
            raise ValueError("the action changed after review; its approval is invalid")
        current = self.policy.check(proposal)
        if current.status == PolicyStatus.DENY:
            return ControlResult("blocked", current, self._policy_decision(proposal, current, reviewed.decision))
        if current.status == PolicyStatus.REVIEW and reviewed.policy_result.status != PolicyStatus.REVIEW:
            return ControlResult("review", current, self._policy_decision(proposal, current, reviewed.decision))
        decision = ControlDecision(
            action_id=proposal.action_id,
            proposal_digest=proposal.digest(),
            outcome=DecisionOutcome.REVIEW,
            confidence=reviewed.decision.confidence,
            reason="caller explicitly approved the reviewed action",
            source="caller",
        )
        return self._execute(proposal, current, decision, "caller")

    def _execute(self, proposal: ActionProposal, policy: PolicyResult, decision: ControlDecision, source: str) -> ControlResult:
        permit = None
        try:
            permit = self.permits.issue(proposal, decision, source)
            result = self.executor.execute(proposal, permit)
            return ControlResult("success", policy, decision, permit=permit, tool_result=result)
        except (PolicyDenied, ReviewRequired) as exc:
            if permit is not None:
                self.permits.revoke(permit)
            current = self.policy.check(proposal)
            status = "review" if isinstance(exc, ReviewRequired) else "blocked"
            return ControlResult(status, current, self._policy_decision(proposal, current, decision, str(exc)))
        except Exception as exc:
            if permit is not None:
                self.permits.revoke(permit)
            return ControlResult("error", policy, decision, error=str(exc))

    @staticmethod
    def _policy_decision(proposal: ActionProposal, policy: PolicyResult, prior: ControlDecision, reason: str | None = None) -> ControlDecision:
        return ControlDecision(
            action_id=proposal.action_id,
            proposal_digest=proposal.digest(),
            outcome=DecisionOutcome.REVIEW if policy.status == PolicyStatus.REVIEW else DecisionOutcome.DENY,
            confidence=prior.confidence,
            reason=reason or policy.reason,
            source="policy",
        )
