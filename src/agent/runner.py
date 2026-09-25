"""Controlled proposal -> decision -> permit -> tool -> observation loop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence
from typing import Protocol
from uuid import uuid4

from ..control.chain import ControlChain, ControlResult
from ..control.controller import DecisionController
from ..control.models import (
    ActionProposal,
    AgentFinish,
    AgentStep,
    AgentTrace,
    ControlDecision,
    ControlledAgentRunRequest,
    Observation,
    PolicyResult,
)
from ..control.permits import ExecutionPermitAuthority
from ..control.policy import DeterministicPolicy
from ..core.decision import DecisionEngine
from ..tools.executor import SandboxToolExecutor


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
        engine: DecisionEngine | None,
        sandbox_root: str | Path,
        planner: AgentPlanner,
        minimum_confidence: float = 0.5,
        control_chain: ControlChain | None = None,
    ):
        self.planner = planner
        if control_chain is None:
            policy = DeterministicPolicy(sandbox_root)
            permits = ExecutionPermitAuthority()
            control_chain = ControlChain(
                DecisionController(engine, policy, minimum_confidence, policy.decision_arguments),
                permits,
                SandboxToolExecutor(policy, permits),
            )
        self.control_chain = control_chain
        self.policy = control_chain.policy
        self.permit_authority = control_chain.permits
        self.controller = control_chain.controller
        self.executor = control_chain.executor
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
        pending = self._pending.pop(key, None)
        if pending is None:
            raise ApprovalError("no pending action matches this approval")
        # Remove before execution: replayed or concurrent approvals cannot run twice.
        if pending.proposal is None or pending.decision is None or pending.policy_result is None:
            raise ApprovalError("pending action state is incomplete")
        if pending.proposal.digest() != pending.proposal_digest:
            raise ApprovalError("the action changed after review; its approval is invalid")
        reviewed = ControlResult("review", pending.policy_result, pending.decision)
        try:
            result = self.control_chain.approve(pending.proposal, reviewed)
        except ValueError as exc:
            raise ApprovalError(str(exc)) from exc
        step = pending.steps[-1]
        self._fill_step(step, result)
        if result.status == "review":
            pending.policy_result = result.policy_result
            pending.decision = result.decision
            self._pending[key] = pending
            return self._trace(
                pending, "approval_required",
                stop_reason="filesystem risk changed; review the updated policy result",
                pending_action=pending.proposal, pending_decision=result.decision,
            )
        if result.status == "blocked":
            return self._trace(pending, "blocked", stop_reason=result.decision.reason)
        if result.status == "error":
            return self._trace(pending, "failed", stop_reason="approved action failed during execution")
        pending.history.append(step.observation)
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
                result = await self.control_chain.run(proposed)
            except Exception as exc:
                state.steps.append(
                    AgentStep(
                        step=step_number, proposal=proposed,
                        execution_status="error", error=str(exc),
                        observation=Observation(status="error", error=str(exc)),
                    )
                )
                return self._trace(state, "failed", stop_reason="control chain failed")

            step = AgentStep(step=step_number, proposal=proposed, execution_status="blocked")
            self._fill_step(step, result)
            state.steps.append(step)
            if result.status == "review":
                state.step_number = step_number
                state.proposal = proposed
                state.proposal_digest = proposed.digest()
                state.policy_result = result.policy_result
                state.decision = result.decision
                self._pending[(state.run_id, proposed.action_id)] = state
                return self._trace(
                    state, "approval_required",
                    stop_reason="explicit approval is required before execution",
                    pending_action=proposed, pending_decision=result.decision,
                )
            state.history.append(step.observation)

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
    def _fill_step(step: AgentStep, result: ControlResult) -> None:
        step.policy_result = result.policy_result
        step.decision = result.decision
        step.permit = result.permit
        step.tool_result = result.tool_result
        step.execution_status = "approval_required" if result.status == "review" else result.status
        step.error = result.error
        if result.status == "success":
            step.observation = Observation(status="success", output=result.tool_result.output)
        elif result.status == "blocked":
            step.observation = Observation(
                status="blocked", output=result.decision.reason, error=result.decision.reason
            )
        elif result.status == "error":
            step.observation = Observation(status="error", error=result.error)

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
