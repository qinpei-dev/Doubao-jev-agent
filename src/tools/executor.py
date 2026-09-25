"""Sandboxed filesystem tools and an exact, shell-free command allowlist."""

import subprocess
import sys
from pathlib import Path
from shutil import which

from ..control.models import ActionProposal, ExecutionPermit, ToolResult
from ..control.errors import PolicyDenied, ReviewRequired
from ..control.permits import ExecutionPermitAuthority
from ..control.policy import DeterministicPolicy


class SandboxToolRegistry:
    """The v0.3 tool registry intentionally contains four fixed operations."""

    names = frozenset({"list_files", "read_file", "write_file", "run_safe_command"})

    def __init__(self, policy: DeterministicPolicy):
        self.policy = policy

    def execute(self, proposal: ActionProposal) -> ToolResult:
        handlers = {
            "list_files": self._list_files,
            "read_file": self._read_file,
            "write_file": self._write_file,
            "run_safe_command": self._run_safe_command,
        }
        if proposal.tool not in handlers:
            raise PermissionError(f"tool is not registered: {proposal.tool}")
        return handlers[proposal.tool](proposal)

    def _list_files(self, proposal: ActionProposal) -> ToolResult:
        directory = self.policy.resolve_for_execution(proposal.arguments.get("path", "."))
        if not directory.is_dir():
            raise NotADirectoryError("list_files target is not a directory")
        names = sorted(child.name for child in directory.iterdir())
        return ToolResult(output="\n".join(names), metadata={"count": len(names)})

    def _read_file(self, proposal: ActionProposal) -> ToolResult:
        path = self.policy.resolve_for_execution(proposal.arguments["path"])
        if not path.is_file():
            raise FileNotFoundError("read_file target does not exist or is not a file")
        return ToolResult(output=path.read_text(encoding="utf-8"))

    def _write_file(self, proposal: ActionProposal) -> ToolResult:
        path = self.policy.resolve_for_execution(proposal.arguments["path"])
        if path.exists() and not path.is_file():
            raise IsADirectoryError("write_file target is not a regular file")
        path.parent.mkdir(parents=True, exist_ok=True)
        content = proposal.arguments["content"]
        path.write_text(content, encoding="utf-8")
        return ToolResult(
            output=f"Wrote {len(content.encode('utf-8'))} bytes to {proposal.arguments['path']}",
            metadata={"path": proposal.arguments["path"]},
        )

    def _run_safe_command(self, proposal: ActionProposal) -> ToolResult:
        command = proposal.arguments["command"]
        if command == "python-version":
            argv = [sys.executable, "--version"]
        else:
            git = which("git")
            if not git:
                raise FileNotFoundError("git executable is unavailable")
            argv = [git, "status"] if command == "git-status" else [git, "diff", "--stat"]
        completed = subprocess.run(
            argv,
            cwd=self.policy.root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            shell=False,
        )
        output = (completed.stdout + completed.stderr).strip()
        if completed.returncode:
            raise RuntimeError(f"safe command exited with status {completed.returncode}: {output}")
        return ToolResult(
            output=output,
            metadata={"command": command, "exit_code": completed.returncode},
        )


class SandboxToolExecutor:
    """Execute only actions accompanied by an approved, one-use permit."""

    def __init__(
        self,
        policy: DeterministicPolicy,
        permit_authority: ExecutionPermitAuthority,
    ):
        self.policy = policy
        self.permit_authority = permit_authority
        self.registry = SandboxToolRegistry(policy)

    def execute(
        self,
        proposal: ActionProposal,
        permit: ExecutionPermit | None = None,
    ) -> ToolResult:
        # Recheck at the boundary so a changed filesystem cannot turn a prior
        # allow into an overwrite. A reviewed action needs a caller-issued permit.
        from ..control.models import PolicyStatus

        current_policy = self.policy.check(proposal)
        if current_policy.status == PolicyStatus.DENY:
            raise PolicyDenied(current_policy.reason)
        if current_policy.status == PolicyStatus.REVIEW and (
            permit is None or permit.decision.value != "review" or permit.approval_source != "caller"
        ):
            raise ReviewRequired(current_policy.reason)
        self.permit_authority.consume(proposal, permit)
        return self.registry.execute(proposal)
