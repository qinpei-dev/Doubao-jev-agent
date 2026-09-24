"""Controlled proposal -> decision -> permit -> tool -> observation loop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence
from typing import Protocol
from uuid import uuid4

from ..control.controller import DecisionController
from ..control.models import (
    ActionProposal,
    AgentFinish,
    AgentStep,
    AgentTrace,
    ControlDecision,
    ControlledAgentRunRequest,
    DecisionOutcome,
    Observation,
    PolicyResult,
    PolicyStatus,
)
from ..control.permits import ExecutionPermitAuthority
from ..control.policy import DeterministicPolicy
from ..core.decision import DecisionEngine
from ..tools.executor import PolicyDenied, ReviewRequired, SandboxToolExecutor


class AgentPlanner(Protocol):
    async def propose(
        self, task: str, history: Sequence[Observation]
    ) -> ActionProposal | AgentFinish: ...


class ApprovalError(ValueError):
    """An approval does not match a currently pending action."""


@dataclass
class _PendingApproval:
    run_id: str
    task: str
    max_steps: int
    step_number: int
    steps: list[AgentStep]
    history: list[Observation]
    proposal: ActionProposal | None = None
    proposal_digest: str = ""
    policy_result: PolicyResult | None = None
    decision: ControlDecision | None = None


class ControlledAgentRunner:
    """In-memory service for controlled runs and explicit review approvals."""

    def __init__(
        self,
        engine: DecisionEngine,
        sandbox_root: str | Path,
        planner: AgentPlanner,
        minimum_confidence: float = 0.5,
    ):
        self.planner = planner
        self.policy = DeterministicPolicy(sandbox_root)
        self.permit_authority = ExecutionPermitAuthority()
        self.controller = DecisionController(engine, self.policy, minimum_confidence)
        self.executor = SandboxToolExecutor(self.policy, self.permit_authority)
        self._pending: dict[tuple[str, str], _PendingApproval] = {}

    async def run(self, task: str, max_steps: int = 5) -> AgentTrace:
        request = ControlledAgentRunRequest(task=task, max_steps=max_steps)
        state = _PendingApproval(
            run_id=str(uuid4()),
            task=request.task,
            max_steps=request.max_steps,
            step_number=1,
            steps=[],
            history=[],
        )
        return await self._run_loop(state, 1)

    async def approve_action(self, action_id: str, run_id: str) -> AgentTrace:
        key = (run_id, action_id)
        pending = self._pending.get(key)
        if pending is None:
            raise ApprovalError("no pending action matches this approval")
        # Remove before awaiting anything: concurrent/replayed approvals cannot
        # execute the same action twice.
        del self._pending[key]
        if pending.proposal is None or pending.decision is None or pending.policy_result is None:
            raise ApprovalError("pending action state is incomplete")
        if pending.proposal.digest() != pending.proposal_digest:
            raise ApprovalError("the action changed after review; its approval is invalid")
        current_policy = self.policy.check(pending.proposal)
        if current_policy.status == PolicyStatus.DENY:
            step = pending.steps[-1]
            step.execution_status = "blocked"
            step.policy_result = current_policy
            step.decision = ControlDecision(
                action_id=action_id,
                proposal_digest=pending.proposal.digest(),
                outcome=DecisionOutcome.DENY,
                reason=current_policy.reason,
                source="policy",
            )
            step.observation = Observation(status="blocked", output=current_policy.reason, error=current_policy.reason)
            return self._trace(pending, "blocked", stop_reason=current_policy.reason)
        if (
            current_policy.status == PolicyStatus.REVIEW
            and pending.policy_result.status != PolicyStatus.REVIEW
        ):
            refreshed_decision = ControlDecision(
                action_id=action_id,
                proposal_digest=pending.proposal.digest(),
                outcome=DecisionOutcome.REVIEW,
                confidence=pending.decision.confidence,
                reason=current_policy.reason,
                source="policy",
            )
            pending.policy_result = current_policy
            pending.decision = refreshed_decision
            step = pending.steps[-1]
            step.policy_result = current_policy
            step.decision = refreshed_decision
            step.execution_status = "approval_required"
            self._pending[key] = pending
            return self._trace(
                pending,
                "approval_required",
                stop_reason="filesystem risk changed; review the updated policy result",
                pending_action=pending.proposal,
                pending_decision=refreshed_decision,
            )

        approval_decision = ControlDecision(
            action_id=action_id,
            proposal_digest=pending.proposal.digest(),
            outcome=DecisionOutcome.REVIEW,
            confidence=pending.decision.confidence,
            reason="caller explicitly approved the reviewed action",
            source="caller",
        )
        permit = None
        try:
            permit = self.permit_authority.issue(pending.proposal, approval_decision, "caller")
            tool_result = self.executor.execute(pending.proposal, permit)
        except PolicyDenied as exc:
            if permit is not None:
                self.permit_authority.revoke(permit)
            step = pending.steps[-1]
            policy_result = self.policy.check(pending.proposal)
            step.policy_result = policy_result
            step.decision = ControlDecision(
                action_id=action_id,
                proposal_digest=pending.proposal.digest(),
                outcome=DecisionOutcome.DENY,
                confidence=pending.decision.confidence,
                reason=str(exc),
                source="policy",
            )
            step.execution_status = "blocked"
            step.observation = Observation(status="blocked", output=str(exc), error=str(exc))
            return self._trace(pending, "blocked", stop_reason=str(exc))
        except Exception as exc:
            if permit is not None:
                self.permit_authority.revoke(permit)
            step = pending.steps[-1]
            step.execution_status = "error"
            step.error = str(exc)
            step.observation = Observation(status="error", error=str(exc))
            return self._trace(pending, "failed", stop_reason="approved action failed during execution")

        observation = Observation(status="success", output=tool_result.output)
        pending.history.append(observation)
        step = pending.steps[-1]
        step.permit = permit
        step.execution_status = "success"
        step.tool_result = tool_result
        step.observation = observation
        # Continue with the same planner history and budget after the approved step.
        return await self._run_loop(pending, pending.step_number + 1)

    async def _run_loop(self, state: _PendingApproval, start_step: int) -> AgentTrace:
        for step_number in range(start_step, state.max_steps + 1):
            try:
                proposed = await self.planner.propose(state.task, tuple(state.history))
            except Exception as exc:
                state.steps.append(
                    AgentStep(step=step_number, execution_status="error", error=str(exc))
                )
                return self._trace(state, "failed", stop_reason="agent planner failed")

            if isinstance(proposed, AgentFinish):
                finish_status = {
                    "completed": "finished",
                    "blocked": "blocked",
                    "failed": "error",
                }[proposed.status]
                state.steps.append(
                    AgentStep(
                        step=step_number,
                        execution_status=finish_status,
                        final_output=proposed.final_output,
                    )
                )
                return self._trace(state, proposed.status, final_output=proposed.final_output)

            if any(step.proposal and step.proposal.action_id == proposed.action_id for step in state.steps):
                state.steps.append(
                    AgentStep(
                        step=step_number,
                        proposal=proposed,
                        execution_status="error",
                        error="agent reused an action_id within the same run",
                    )
                )
                return self._trace(state, "failed", stop_reason="duplicate action_id")

            try:
                policy_result, decision = await self.controller.decide(proposed)
            except Exception as exc:
                state.steps.append(
                    AgentStep(
                        step=step_number,
                        proposal=proposed,
                        execution_status="error",
                        error=str(exc),
                        observation=Observation(status="error", error=str(exc)),
                    )
                )
                return self._trace(state, "failed", stop_reason="decision controller failed")

            if (
                decision.action_id != proposed.action_id
                or decision.proposal_digest != proposed.digest()
            ):
                state.steps.append(
                    AgentStep(
                        step=step_number,
                        proposal=proposed,
                        policy_result=policy_result,
                        decision=decision,
                        execution_status="error",
                        error="control decision is not bound to this proposal",
                    )
                )
                return self._trace(state, "failed", stop_reason="action binding validation failed")

            if decision.outcome == DecisionOutcome.DENY:
                observation = Observation(status="blocked", output=decision.reason, error=decision.reason)
                state.steps.append(
                    AgentStep(
                        step=step_number,
                        proposal=proposed,
                        policy_result=policy_result,
                        decision=decision,
                        execution_status="blocked",
                        observation=observation,
                    )
                )
                state.history.append(observation)
                continue

            if decision.outcome == DecisionOutcome.REVIEW:
                state.steps.append(
                    AgentStep(
                        step=step_number,
                        proposal=proposed,
                        policy_result=policy_result,
                        decision=decision,
                        execution_status="approval_required",
                    )
                )
                state.step_number = step_number
                state.proposal = proposed
                state.proposal_digest = proposed.digest()
                state.policy_result = policy_result
                state.decision = decision
                self._pending[(state.run_id, proposed.action_id)] = state
                return self._trace(
                    state,
                    "approval_required",
                    stop_reason="explicit approval is required before execution",
                    pending_action=proposed,
                    pending_decision=decision,
                )

            permit = None
            try:
                permit = self.permit_authority.issue(proposed, decision, "jev")
                tool_result = self.executor.execute(proposed, permit)
            except ReviewRequired as exc:
                if permit is not None:
                    self.permit_authority.revoke(permit)
                refreshed_policy = self.policy.check(proposed)
                review_decision = ControlDecision(
                    action_id=proposed.action_id,
                    proposal_digest=proposed.digest(),
                    outcome=DecisionOutcome.REVIEW,
                    confidence=decision.confidence,
                    reason=str(exc),
                    source="policy",
                )
                state.steps.append(
                    AgentStep(
                        step=step_number,
                        proposal=proposed,
                        policy_result=refreshed_policy,
                        decision=review_decision,
                        execution_status="approval_required",
                    )
                )
                state.step_number = step_number
                state.proposal = proposed
                state.proposal_digest = proposed.digest()
                state.policy_result = refreshed_policy
                state.decision = review_decision
                self._pending[(state.run_id, proposed.action_id)] = state
                return self._trace(
                    state,
                    "approval_required",
                    stop_reason="filesystem risk changed before execution",
                    pending_action=proposed,
                    pending_decision=review_decision,
                )
            except PolicyDenied as exc:
                if permit is not None:
                    self.permit_authority.revoke(permit)
                policy_result = self.policy.check(proposed)
                deny_decision = ControlDecision(
                    action_id=proposed.action_id,
                    proposal_digest=proposed.digest(),
                    outcome=DecisionOutcome.DENY,
                    confidence=decision.confidence,
                    reason=str(exc),
                    source="policy",
                )
                blocked_observation = Observation(status="blocked", output=str(exc), error=str(exc))
                state.steps.append(
                    AgentStep(
                        step=step_number,
                        proposal=proposed,
                        policy_result=policy_result,
                        decision=deny_decision,
                        execution_status="blocked",
                        observation=blocked_observation,
                    )
                )
                state.history.append(blocked_observation)
                continue
            except Exception as exc:
                if permit is not None:
                    self.permit_authority.revoke(permit)
                failure_observation = Observation(status="error", error=str(exc))
                state.steps.append(
                    AgentStep(
                        step=step_number,
                        proposal=proposed,
                        policy_result=policy_result,
                        decision=decision,
                        execution_status="error",
                        error=str(exc),
                        observation=failure_observation,
                    )
                )
                state.history.append(failure_observation)
                continue

            observation = Observation(status="success", output=tool_result.output)
            state.history.append(observation)
            state.steps.append(
                AgentStep(
                    step=step_number,
                    proposal=proposed,
                    policy_result=policy_result,
                    decision=decision,
                    permit=permit,
                    execution_status="success",
                    tool_result=tool_result,
                    observation=observation,
                )
            )

        # Check whether the planner has finished after using its action budget.
        try:
            final_plan = await self.planner.propose(state.task, tuple(state.history))
        except Exception as exc:
            state.steps.append(AgentStep(step=state.max_steps + 1, execution_status="error", error=str(exc)))
            return self._trace(state, "failed", stop_reason="agent planner failed")
        if isinstance(final_plan, AgentFinish):
            finish_status = {
                "completed": "finished",
                "blocked": "blocked",
                "failed": "error",
            }[final_plan.status]
            state.steps.append(
                AgentStep(
                    step=state.max_steps + 1,
                    execution_status=finish_status,
                    final_output=final_plan.final_output,
                )
            )
            return self._trace(state, final_plan.status, final_output=final_plan.final_output)
        state.steps.append(
            AgentStep(
                step=state.max_steps + 1,
                proposal=final_plan,
                execution_status="blocked",
                observation=Observation(status="blocked", error="max_steps reached"),
            )
        )
        return self._trace(state, "blocked", stop_reason="max_steps reached")

    @staticmethod
    def _trace(
        state: _PendingApproval,
        status: str,
        *,
        final_output: str | None = None,
        stop_reason: str | None = None,
        pending_action: ActionProposal | None = None,
        pending_decision: ControlDecision | None = None,
    ) -> AgentTrace:
        return AgentTrace(
            run_id=state.run_id,
            task=state.task,
            status=status,
            steps=list(state.steps),
            final_output=final_output,
            stop_reason=stop_reason,
            pending_action=pending_action,
            pending_decision=pending_decision,
        )
