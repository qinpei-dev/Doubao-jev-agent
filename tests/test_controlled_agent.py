"""Offline control, permit, sandbox, approval, and Agent loop tests."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agent import ApprovalError, ControlledAgentRunner, DeterministicDemoAgent
from src.control.controller import DecisionController
from src.control.models import (
    ActionProposal,
    AgentFinish,
    ControlDecision,
    DecisionOutcome,
    ExecutionPermit,
    Observation,
    PolicyStatus,
)
from src.control.permits import ExecutionPermitAuthority, PermitError
from src.control.policy import DeterministicPolicy
from src.core.decision import DecisionEngine
from src.core.models import DecisionRequest, DecisionResult
from src.jev.client import JEVClient
from src.tools.executor import SandboxToolExecutor


class ChoiceClient(JEVClient):
    def __init__(self, choice="allow", confidence=0.9):
        self.choice = choice
        self.confidence = confidence
        self.calls = []

    async def decide(self, request: DecisionRequest) -> DecisionResult:
        self.calls.append(request)
        return DecisionResult(decision=self.choice, confidence=self.confidence, reason="test choice")


class InvalidChoiceClient(JEVClient):
    async def decide(self, request: DecisionRequest) -> DecisionResult:
        return DecisionResult(decision="unknown", confidence=0.9, reason="bad response")


class MutatingChoiceClient(JEVClient):
    def __init__(self, action):
        self.action = action

    async def decide(self, request: DecisionRequest) -> DecisionResult:
        self.action.arguments["content"] = "changed while waiting for JEV"
        return DecisionResult(decision="allow", confidence=0.9, reason="test choice")


class SingleActionPlanner:
    def __init__(self, proposal):
        self.proposal = proposal
        self.histories = []
        self.proposed = False

    async def propose(self, task, history):
        self.histories.append(tuple(history))
        if not self.proposed:
            self.proposed = True
            return self.proposal
        if history and history[-1].status == "blocked":
            return AgentFinish(final_output="denied observation received", status="blocked")
        if history and history[-1].status == "error":
            return AgentFinish(final_output="tool error received", status="failed")
        return AgentFinish(final_output="finished after observation")


class EndlessPlanner:
    async def propose(self, task, history):
        return ActionProposal(
            tool="read_file", arguments={"path": "README.md"}, description="repeat a safe read"
        )


def proposal(tool="read_file", arguments=None, description="test action"):
    if arguments is None:
        arguments = {"path": "README.md"}
    return ActionProposal(tool=tool, arguments=arguments, description=description)


def make_runner(root, *, client=None, planner=None, minimum_confidence=0.5):
    client = client or ChoiceClient()
    runner = ControlledAgentRunner(
        DecisionEngine(client),
        sandbox_root=root,
        planner=planner or DeterministicDemoAgent(),
        minimum_confidence=minimum_confidence,
    )
    return runner, client


def test_action_proposal_is_generic_but_sandbox_policy_validates_arguments(tmp_path):
    action = proposal("write_file", {"path": "output/x.txt", "content": "hello"})
    assert action.action_id
    assert action.tool == "write_file"
    generic = ActionProposal(tool="remote.search", arguments={"query": "permit"}, description="search")
    assert generic.tool == "remote.search"
    policy = DeterministicPolicy(tmp_path)
    assert policy.check(generic).status == PolicyStatus.DENY
    malformed = ActionProposal(tool="read_file", arguments={"path": "README.md", "mode": "rb"}, description="bad args")
    assert policy.check(malformed).status == PolicyStatus.DENY


def test_policy_denies_traversal_and_absolute_paths(tmp_path):
    policy = DeterministicPolicy(tmp_path / "sandbox")
    traversal = policy.check(proposal(arguments={"path": "../outside.txt"}))
    absolute = policy.check(proposal(arguments={"path": "C:\\Windows\\win.ini"}))
    assert traversal.status == PolicyStatus.DENY
    assert "traversal" in traversal.reason
    assert absolute.status == PolicyStatus.DENY


def test_policy_denies_tool_not_in_controlled_registry(tmp_path):
    unregistered = proposal().model_copy(update={"tool": "shell"})
    result = DeterministicPolicy(tmp_path).check(unregistered)
    assert result.status == PolicyStatus.DENY
    assert "not registered" in result.reason


def test_policy_denies_unresolvable_path(tmp_path):
    result = DeterministicPolicy(tmp_path).check(proposal(arguments={"path": "bad\x00path"}))
    assert result.status == PolicyStatus.DENY
    assert "null byte" in result.reason


def test_policy_denies_symlink_that_resolves_outside_sandbox(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable in this environment: {exc}")
    result = DeterministicPolicy(root).check(proposal(arguments={"path": "link/secret.txt"}))
    assert result.status == PolicyStatus.DENY
    assert "outside" in result.reason


def test_policy_marks_existing_file_overwrite_for_review(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "existing.txt").write_text("before", encoding="utf-8")
    action = proposal("write_file", {"path": "existing.txt", "content": "after"})
    result = DeterministicPolicy(root).check(action)
    assert result.status == PolicyStatus.REVIEW
    assert result.risk_context["destructive"] is True
    assert result.risk_context["overwrites_existing"] is True


def test_policy_enforces_exact_safe_command_allowlist(tmp_path):
    policy = DeterministicPolicy(tmp_path / "sandbox")
    allowed = proposal("run_safe_command", {"command": "python-version"})
    rejected = proposal("run_safe_command", {"command": "powershell -Command whoami"})
    assert policy.check(allowed).status == PolicyStatus.PASS
    assert policy.check(rejected).status == PolicyStatus.DENY


@pytest.mark.parametrize("choice", ["allow", "review", "deny"])
def test_decision_controller_maps_jev_choice_to_control_outcome(tmp_path, choice):
    # Keep JEV's output structured while verifying all application outcomes.
    policy = DeterministicPolicy(tmp_path / "sandbox")
    controller = DecisionController(DecisionEngine(ChoiceClient(choice)), policy)
    checked, decision = asyncio.run(controller.decide(proposal()))
    assert checked.status == PolicyStatus.PASS
    assert decision.outcome.value == choice
    assert decision.confidence == 0.9
    assert decision.action_id


def test_policy_deny_short_circuits_jev(tmp_path):
    client = ChoiceClient()
    controller = DecisionController(DecisionEngine(client), DeterministicPolicy(tmp_path))
    _, decision = asyncio.run(controller.decide(proposal(arguments={"path": "../outside"})))
    assert decision.outcome == DecisionOutcome.DENY
    assert decision.source == "policy"
    assert client.calls == []


def test_invalid_jev_response_cannot_become_control_decision(tmp_path):
    controller = DecisionController(DecisionEngine(InvalidChoiceClient()), DeterministicPolicy(tmp_path))
    with pytest.raises(ValueError, match="outside the allowed options"):
        asyncio.run(controller.decide(proposal()))


def test_action_mutated_while_waiting_for_jev_is_rejected(tmp_path):
    action = proposal("write_file", {"path": "new.txt", "content": "original"})
    controller = DecisionController(
        DecisionEngine(MutatingChoiceClient(action)), DeterministicPolicy(tmp_path)
    )
    with pytest.raises(ValueError, match="changed while its JEV decision was pending"):
        asyncio.run(controller.decide(action))


def test_sandbox_write_content_is_redacted_from_provider_context(tmp_path):
    client = ChoiceClient()
    controller = DecisionController(DecisionEngine(client), DeterministicPolicy(tmp_path))
    asyncio.run(controller.decide(proposal("write_file", {"path": "new.txt", "content": "secret"})))
    assert "secret" not in client.calls[0].task
    assert '"content_length": 6' in client.calls[0].task


def test_low_confidence_allow_becomes_review_and_confidence_is_bounded(tmp_path):
    controller = DecisionController(
        DecisionEngine(ChoiceClient("allow", 0.2)), DeterministicPolicy(tmp_path), minimum_confidence=0.5
    )
    _, decision = asyncio.run(controller.decide(proposal()))
    assert decision.outcome == DecisionOutcome.REVIEW
    assert decision.source == "confidence"
    assert decision.confidence == 0.2
    with pytest.raises(ValidationError):
        DecisionResult(decision="allow", confidence=1.01, reason="invalid")


def approved_decision(action):
    return ControlDecision(
        action_id=action.action_id,
        proposal_digest=action.digest(),
        outcome=DecisionOutcome.ALLOW,
        confidence=0.9,
        reason="allow",
        source="jev",
    )


def test_permit_is_valid_for_bound_action_and_single_use(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "README.md").write_text("read me", encoding="utf-8")
    policy = DeterministicPolicy(root)
    authority = ExecutionPermitAuthority()
    executor = SandboxToolExecutor(policy, authority)
    action = proposal()
    permit = authority.issue(action, approved_decision(action), "jev")
    assert executor.execute(action, permit).output == "read me"
    with pytest.raises(PermitError, match="invalid or does not match"):
        executor.execute(action, permit)


def test_permit_wrong_action_rejected(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "README.md").write_text("read me", encoding="utf-8")
    authority = ExecutionPermitAuthority()
    policy = DeterministicPolicy(root)
    from src.tools.executor import SandboxToolExecutor

    executor = SandboxToolExecutor(policy, authority)
    original = proposal()
    permit = authority.issue(original, approved_decision(original), "jev")
    changed = original.model_copy(update={"action_id": "another-action"})
    with pytest.raises(PermitError, match="invalid or does not match"):
        executor.execute(changed, permit)


def test_rejected_or_missing_permit_cannot_execute(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "README.md").write_text("read me", encoding="utf-8")
    action = proposal()
    executor_authority = ExecutionPermitAuthority()
    from src.tools.executor import SandboxToolExecutor

    executor = SandboxToolExecutor(DeterministicPolicy(root), executor_authority)
    with pytest.raises(PermitError, match="required"):
        executor.execute(action)
    rejected = ExecutionPermit(
        action_id=action.action_id,
        tool=action.tool,
        decision=DecisionOutcome.DENY,
        approved=False,
        approval_source="jev",
        proposal_digest=action.digest(),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    with pytest.raises(PermitError, match="not approved"):
        executor.execute(action, rejected)


def test_executor_performs_real_read_and_write(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "input.txt").write_text("source", encoding="utf-8")
    policy = DeterministicPolicy(root)
    authority = ExecutionPermitAuthority()
    from src.tools.executor import SandboxToolExecutor

    executor = SandboxToolExecutor(policy, authority)
    read_action = proposal(arguments={"path": "input.txt"})
    read = executor.execute(read_action, authority.issue(read_action, approved_decision(read_action), "jev"))
    assert read.output == "source"
    write_action = proposal("write_file", {"path": "output/result.txt", "content": "actual write"})
    write = executor.execute(write_action, authority.issue(write_action, approved_decision(write_action), "jev"))
    assert "Wrote" in write.output
    assert (root / "output" / "result.txt").read_text(encoding="utf-8") == "actual write"


def test_executor_runs_only_a_fixed_safe_command(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    policy = DeterministicPolicy(root)
    authority = ExecutionPermitAuthority()
    from src.tools.executor import SandboxToolExecutor

    executor = SandboxToolExecutor(policy, authority)
    action = proposal("run_safe_command", {"command": "python-version"})
    result = executor.execute(action, authority.issue(action, approved_decision(action), "jev"))
    assert result.metadata["exit_code"] == 0
    assert "Python" in result.output


def test_executor_rejects_policy_escape_even_with_a_valid_permit(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    action = proposal(arguments={"path": "../outside.txt"})
    authority = ExecutionPermitAuthority()
    # A forged but otherwise allowed decision still cannot get past the path policy.
    permit = authority.issue(action, approved_decision(action), "jev")
    from src.tools.executor import SandboxToolExecutor

    with pytest.raises(PermissionError, match="traversal"):
        SandboxToolExecutor(DeterministicPolicy(root), authority).execute(action, permit)


def test_executor_error_is_reported_to_agent_trace(tmp_path):
    missing_read = proposal(arguments={"path": "missing.txt"})
    planner = SingleActionPlanner(missing_read)
    runner, _ = make_runner(tmp_path, planner=planner)
    trace = asyncio.run(runner.run("read a missing file", max_steps=2))
    assert trace.status == "failed"
    assert trace.steps[0].execution_status == "error"
    assert "does not exist" in trace.steps[0].error
    assert planner.histories[1][0].status == "error"


def test_review_prevents_execution_until_matching_approval(tmp_path, monkeypatch):
    root = tmp_path / "sandbox"
    root.mkdir()
    target = root / "existing.txt"
    target.write_text("before", encoding="utf-8")
    action = proposal("write_file", {"path": "existing.txt", "content": "after"})
    runner, _ = make_runner(root, planner=SingleActionPlanner(action))
    calls = []
    real_execute = runner.executor.execute

    def tracked_execute(*args, **kwargs):
        calls.append(args[0].action_id)
        return real_execute(*args, **kwargs)

    monkeypatch.setattr(runner.executor, "execute", tracked_execute)
    pending = asyncio.run(runner.run("overwrite existing", max_steps=3))
    assert pending.status == "approval_required"
    assert target.read_text(encoding="utf-8") == "before"
    assert calls == []
    assert pending.pending_action.action_id == action.action_id
    completed = asyncio.run(runner.approve_action(action.action_id, run_id=pending.run_id))
    assert completed.status == "completed"
    assert target.read_text(encoding="utf-8") == "after"
    assert calls == [action.action_id]
    assert completed.steps[0].permit.approval_source == "caller"


def test_wrong_review_action_id_is_rejected_without_execution(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    target = root / "existing.txt"
    target.write_text("unchanged", encoding="utf-8")
    action = proposal("write_file", {"path": "existing.txt", "content": "changed"})
    runner, _ = make_runner(root, planner=SingleActionPlanner(action))
    pending = asyncio.run(runner.run("overwrite", max_steps=2))
    with pytest.raises(ApprovalError, match="no pending action"):
        asyncio.run(runner.approve_action("wrong-action", run_id=pending.run_id))
    assert target.read_text(encoding="utf-8") == "unchanged"
    assert (pending.run_id, action.action_id) in runner._pending


def test_changed_action_invalidates_old_review(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    target = root / "existing.txt"
    target.write_text("unchanged", encoding="utf-8")
    action = proposal("write_file", {"path": "existing.txt", "content": "approved content"})
    runner, _ = make_runner(root, planner=SingleActionPlanner(action))
    pending = asyncio.run(runner.run("overwrite", max_steps=2))
    runner._pending[(pending.run_id, action.action_id)].proposal.arguments["content"] = "tampered"
    with pytest.raises(ApprovalError, match="action changed"):
        asyncio.run(runner.approve_action(action.action_id, run_id=pending.run_id))
    assert target.read_text(encoding="utf-8") == "unchanged"


def test_jev_review_requires_explicit_approval(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    action = proposal("write_file", {"path": "new.txt", "content": "approved"})
    runner, _ = make_runner(root, client=ChoiceClient("review"), planner=SingleActionPlanner(action))
    pending = asyncio.run(runner.run("write file", max_steps=2))
    assert pending.status == "approval_required"
    assert not (root / "new.txt").exists()
    approved = asyncio.run(runner.approve_action(action.action_id, run_id=pending.run_id))
    assert approved.status == "completed"
    assert (root / "new.txt").read_text(encoding="utf-8") == "approved"


def test_new_overwrite_risk_before_execution_returns_to_review(tmp_path, monkeypatch):
    root = tmp_path / "sandbox"
    root.mkdir()
    action = proposal("write_file", {"path": "new.txt", "content": "new value"})
    runner, _ = make_runner(root, planner=SingleActionPlanner(action))
    original_check = runner.policy.check
    checks = 0

    def create_target_after_decision(proposed):
        nonlocal checks
        checks += 1
        result = original_check(proposed)
        if checks == 1:
            (root / "new.txt").write_text("appeared after decision", encoding="utf-8")
        return result

    monkeypatch.setattr(runner.policy, "check", create_target_after_decision)
    pending = asyncio.run(runner.run("write a new file", max_steps=3))
    assert pending.status == "approval_required"
    assert pending.steps[0].permit is None
    assert (root / "new.txt").read_text(encoding="utf-8") == "appeared after decision"
    approved = asyncio.run(runner.approve_action(action.action_id, run_id=pending.run_id))
    assert approved.status == "completed"
    assert (root / "new.txt").read_text(encoding="utf-8") == "new value"


def test_demo_loop_reads_real_readme_writes_summary_and_feeds_observations(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "README.md").write_text(
        "# Demo Project\n\n[English](README.md) | [中文](README_CN.md)\n\n"
        "A project about controlled execution.\n\n## Features\n\nMore text.\n",
        encoding="utf-8",
    )
    runner, _ = make_runner(root)
    trace = asyncio.run(runner.run("summarize README.md", max_steps=5))
    assert trace.status == "completed"
    assert [step.proposal.tool for step in trace.steps if step.proposal] == ["read_file", "write_file"]
    output = (root / "output" / "summary.md").read_text(encoding="utf-8")
    assert "Demo Project" in output
    assert "controlled execution" in output
    assert "[English]" not in output
    assert "Features" not in output
    assert all(step.permit is not None for step in trace.steps if step.proposal)


def test_default_demo_planner_blocks_unsupported_task(tmp_path):
    runner, client = make_runner(tmp_path)
    trace = asyncio.run(runner.run("delete all files", max_steps=3))
    assert trace.status == "blocked"
    assert trace.steps[0].proposal is None
    assert trace.steps[0].execution_status == "blocked"
    assert client.calls == []
    assert list(tmp_path.iterdir()) == []


def test_deny_blocks_executor_and_skips_jev(tmp_path, monkeypatch):
    action = proposal(arguments={"path": "../outside.txt"})
    planner = SingleActionPlanner(action)
    runner, client = make_runner(tmp_path, planner=planner)
    calls = []
    monkeypatch.setattr(runner.executor, "execute", lambda *args, **kwargs: calls.append(args))
    trace = asyncio.run(runner.run("read outside", max_steps=3))
    assert trace.status == "blocked"
    assert trace.steps[0].decision.outcome == DecisionOutcome.DENY
    assert trace.steps[0].policy_result.status == PolicyStatus.DENY
    assert calls == []
    assert client.calls == []
    assert planner.histories[1][0].status == "blocked"


def test_max_steps_is_enforced(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "README.md").write_text("read", encoding="utf-8")
    runner, _ = make_runner(root, planner=EndlessPlanner())
    trace = asyncio.run(runner.run("repeat", max_steps=1))
    assert trace.status == "blocked"
    assert trace.stop_reason == "max_steps reached"
    assert trace.steps[-1].execution_status == "blocked"


def test_observation_is_passed_back_to_planner(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "README.md").write_text("observed source", encoding="utf-8")
    planner = SingleActionPlanner(proposal())
    runner, _ = make_runner(root, planner=planner)
    trace = asyncio.run(runner.run("read", max_steps=2))
    assert trace.status == "completed"
    assert planner.histories[0] == ()
    assert planner.histories[1][0].output == "observed source"


def test_deterministic_policy_low_confidence_and_approval_trace_fields(tmp_path):
    existing = tmp_path / "existing.txt"
    existing.write_text("before", encoding="utf-8")
    action = proposal("write_file", {"path": "existing.txt", "content": "after"})
    runner, _ = make_runner(tmp_path, planner=SingleActionPlanner(action))
    trace = asyncio.run(runner.run("overwrite", max_steps=2))
    assert trace.status == "approval_required"
    assert trace.steps[0].policy_result.risk_context["overwrites_existing"] is True
    assert trace.steps[0].permit is None
    assert trace.pending_decision.source == "policy"
