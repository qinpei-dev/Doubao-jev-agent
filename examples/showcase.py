"""Screenshot-friendly, offline demonstration of the v0.3 controlled execution chain."""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from src.agent import ControlledAgentRunner
from src.control.models import ActionProposal, AgentFinish, AgentTrace, Observation
from src.core.decision import DecisionEngine
from src.core.models import DecisionRequest, DecisionResult
from src.jev.client import JEVClient


class OneActionPlanner:
    """Propose one real sandbox action, then stop after its observation."""

    def __init__(self, proposal: ActionProposal):
        self.proposal = proposal
        self.proposed = False

    async def propose(self, task: str, history: tuple[Observation, ...]):
        if not self.proposed:
            self.proposed = True
            return self.proposal
        status = "blocked" if history and history[-1].status == "blocked" else "completed"
        return AgentFinish(final_output="Showcase action finished.", status=status)


class CountingControlProvider(JEVClient):
    def __init__(self):
        self.calls = 0

    async def decide(self, request: DecisionRequest) -> DecisionResult:
        self.calls += 1
        return DecisionResult(decision="allow", confidence=0.9, reason="offline control demo")


@dataclass
class Scenario:
    runner: ControlledAgentRunner
    client: CountingControlProvider
    executor_calls: list[str]
    trace: AgentTrace


async def _run(root: Path, proposal: ActionProposal) -> Scenario:
    client = CountingControlProvider()
    runner = ControlledAgentRunner(
        DecisionEngine(client), root, OneActionPlanner(proposal)
    )
    calls: list[str] = []
    execute = runner.executor.execute

    def count_execute(action, permit=None):
        calls.append(action.action_id)
        return execute(action, permit)

    runner.executor.execute = count_execute
    trace = await runner.run(proposal.description, max_steps=1)
    return Scenario(runner, client, calls, trace)


def _step(trace: AgentTrace):
    step = trace.steps[0]
    assert step.proposal and step.policy_result and step.decision
    return step


def _row(label: str, value: str) -> str:
    return f"{label:<11} {value}"


def _render(allowed: Scenario, reviewed: Scenario, approved: AgentTrace,
            denied: Scenario) -> str:
    allow = _step(allowed.trace)
    review = _step(reviewed.trace)
    after = _step(approved)
    deny = _step(denied.trace)
    assert allow.permit and allow.tool_result and allow.execution_status == "success"
    assert review.permit is None and review.execution_status == "approval_required"
    assert after.permit and after.tool_result and after.execution_status == "success"
    assert deny.permit is None and deny.execution_status == "blocked"
    assert allowed.client.calls == 1 and len(allowed.executor_calls) == 1
    assert reviewed.client.calls == 0 and len(reviewed.executor_calls) == 1
    assert denied.client.calls == 0 and denied.executor_calls == []
    assert approved.run_id == reviewed.trace.run_id
    return "\n".join([
        "CONTROLLED AGENT EXECUTION",
        "",
        "SAFE ACTION",
        _row("Agent", "read README.md"),
        _row("Policy", allow.policy_result.status.value.upper()),
        _row("JEV (mock)", f"{allow.decision.outcome.value.upper()} {allow.decision.confidence:.2f}"),
        _row("Permit", "ISSUED"),
        _row("Executor", "SUCCESS"),
        _row("Result", "EXECUTED"),
        "",
        "SENSITIVE ACTION",
        _row("Agent", "overwrite output/existing.txt"),
        _row("Policy", review.policy_result.status.value.upper()),
        _row("JEV", "NOT CALLED"),
        _row("Permit", "NONE"),
        _row("Executor", "NOT CALLED"),
        _row("Result", "WAITING FOR APPROVAL"),
        "",
        _row("Caller", "APPROVE"),
        _row("Permit", "ISSUED"),
        _row("Executor", "SUCCESS"),
        _row("Result", "EXECUTED AFTER APPROVAL"),
        "",
        "FORBIDDEN ACTION",
        _row("Agent", "read ../secret.txt"),
        _row("Policy", deny.policy_result.status.value.upper()),
        _row("JEV", "NOT CALLED"),
        _row("Permit", "NONE"),
        _row("Executor", "NOT CALLED"),
        _row("Result", "BLOCKED"),
    ])


async def run_showcase() -> str:
    """Run all three actions against disposable real files and return verified output."""
    with TemporaryDirectory(prefix="controlled-agent-showcase-") as sandbox:
        root = Path(sandbox)
        (root / "README.md").write_text(
            (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        output = root / "output" / "existing.txt"
        output.parent.mkdir()
        output.write_text("before approval\n", encoding="utf-8")

        allowed = await _run(root, ActionProposal(
            tool="read_file", arguments={"path": "README.md"},
            description="Read the sandbox README.md",
        ))
        assert _step(allowed.trace).tool_result.output == (root / "README.md").read_text(encoding="utf-8")

        reviewed = await _run(root, ActionProposal(
            tool="write_file", arguments={"path": "output/existing.txt", "content": "after approval\n"},
            description="Overwrite an existing sandbox file",
        ))
        assert reviewed.trace.status == "approval_required"
        assert output.read_text(encoding="utf-8") == "before approval\n"
        assert reviewed.executor_calls == []
        # The runner updates the same step when approval resumes; keep the waiting snapshot.
        reviewed.trace = reviewed.trace.model_copy(deep=True)
        approved = await reviewed.runner.approve_action(
            reviewed.trace.pending_action.action_id, reviewed.trace.run_id
        )
        assert output.read_text(encoding="utf-8") == "after approval\n"

        denied = await _run(root, ActionProposal(
            tool="read_file", arguments={"path": "../secret.txt"},
            description="Try to read outside the sandbox",
        ))
        return _render(allowed, reviewed, approved, denied)


if __name__ == "__main__":
    print(asyncio.run(run_showcase()))
