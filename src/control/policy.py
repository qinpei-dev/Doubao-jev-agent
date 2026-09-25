"""Deterministic checks that run before JEV and again at execution time."""

from pathlib import Path, PurePosixPath, PureWindowsPath

from .models import (
    ActionProposal,
    CONTROLLED_TOOL_NAMES,
    PolicyResult,
    PolicyStatus,
    SAFE_COMMANDS,
)


class DeterministicPolicy:
    def __init__(self, sandbox_root: str | Path):
        root = Path(sandbox_root).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("sandbox_root must be a directory")

    def check(self, proposal: ActionProposal) -> PolicyResult:
        tool = proposal.tool
        risk = {
            "tool": tool,
            "writes_files": tool == "write_file",
            "destructive": False,
            "sandboxed": tool in {"list_files", "read_file", "write_file"},
        }

        if tool not in CONTROLLED_TOOL_NAMES:
            return PolicyResult(
                status=PolicyStatus.DENY,
                reason="tool is not registered in the controlled sandbox registry",
                risk_context=risk,
            )

        schemas = {
            "list_files": ({"path"}, set()),
            "read_file": ({"path"}, {"path"}),
            "write_file": ({"path", "content"}, {"path", "content"}),
            "run_safe_command": ({"command"}, {"command"}),
        }
        accepted, required = schemas[tool]
        args = proposal.arguments
        if set(args) - accepted or required - set(args):
            return PolicyResult(status=PolicyStatus.DENY, reason=f"invalid arguments for {tool}", risk_context=risk)
        for key in ("path", "content", "command"):
            if key in args and not isinstance(args[key], str):
                return PolicyResult(status=PolicyStatus.DENY, reason=f"{key} must be a string", risk_context=risk)
        if "path" in args and not args["path"].strip():
            return PolicyResult(status=PolicyStatus.DENY, reason="path must not be blank", risk_context=risk)

        if tool == "run_safe_command":
            command = proposal.arguments["command"]
            if command not in SAFE_COMMANDS:
                return PolicyResult(
                    status=PolicyStatus.DENY,
                    reason="command is not in the safe command allowlist",
                    risk_context=risk,
                )
            risk["command"] = command
            return PolicyResult(
                status=PolicyStatus.PASS,
                reason="command is in the exact read-only allowlist",
                risk_context=risk,
            )

        raw_path = proposal.arguments.get("path", ".")
        candidate, relative, error = self._resolve_sandbox_path(raw_path)
        if error:
            return PolicyResult(
                status=PolicyStatus.DENY,
                reason=error,
                risk_context=risk,
            )

        risk["path"] = relative
        if tool == "write_file" and candidate.exists():
            if candidate.is_dir():
                return PolicyResult(
                    status=PolicyStatus.DENY,
                    reason="write_file cannot replace a directory",
                    risk_context={**risk, "destructive": True},
                    normalized_path=relative,
                )
            return PolicyResult(
                status=PolicyStatus.REVIEW,
                reason="writing an existing file requires explicit caller approval",
                risk_context={**risk, "destructive": True, "overwrites_existing": True},
                normalized_path=relative,
            )

        return PolicyResult(
            status=PolicyStatus.PASS,
            reason="path is inside the configured sandbox",
            risk_context=risk,
            normalized_path=relative,
        )

    @staticmethod
    def decision_arguments(proposal: ActionProposal) -> dict:
        """Hide sandbox write contents from an external decision provider."""
        arguments = dict(proposal.arguments)
        if proposal.tool == "write_file" and isinstance(arguments.get("content"), str):
            arguments["content_length"] = len(arguments.pop("content"))
        return arguments

    def resolve_for_execution(self, raw_path: str) -> Path:
        candidate, _, error = self._resolve_sandbox_path(raw_path)
        if error or candidate is None:
            raise PermissionError(error or "path is outside the sandbox")
        return candidate

    def _resolve_sandbox_path(self, raw_path: str) -> tuple[Path | None, str | None, str | None]:
        if "\x00" in raw_path:
            return None, None, "path contains a null byte and is denied by the sandbox policy"
        windows_path = PureWindowsPath(raw_path)
        normalized = raw_path.replace("\\", "/")
        posix_path = PurePosixPath(normalized)
        if windows_path.is_absolute() or windows_path.drive or posix_path.is_absolute():
            return None, None, "absolute paths are denied by the sandbox policy"
        if ".." in posix_path.parts:
            return None, None, "path traversal is denied by the sandbox policy"
        parts = [part for part in posix_path.parts if part not in {"", "."}]
        try:
            candidate = (self.root.joinpath(*parts)).resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            return None, None, "path could not be resolved by the sandbox policy"
        try:
            relative = candidate.relative_to(self.root).as_posix()
        except ValueError:
            return None, None, "resolved path is outside the sandbox"
        return candidate, relative or ".", None
