"""A no-key deterministic planner for the README summary demonstration."""

from collections.abc import Sequence

from ..control.models import ActionProposal, AgentFinish, Observation


class DeterministicDemoAgent:
    """Read README.md, make a short deterministic summary, then write it."""

    async def propose(
        self, task: str, history: Sequence[Observation]
    ) -> ActionProposal | AgentFinish:
        task_text = task.casefold()
        if "readme" not in task_text or not any(
            word in task_text for word in ("summary", "summar", "摘要", "总结")
        ):
            return AgentFinish(
                final_output="The bundled deterministic planner only supports summarizing README.md.",
                status="blocked",
            )
        if history and history[-1].status == "blocked":
            return AgentFinish(
                final_output=history[-1].error or history[-1].output or "The action was blocked.",
                status="blocked",
            )
        if history and history[-1].status == "error":
            return AgentFinish(
                final_output=history[-1].error or "The tool action failed.", status="failed"
            )
        successful_reads = [
            item for item in history if item.status == "success" and item.output
        ]
        if not successful_reads:
            return ActionProposal(
                tool="read_file",
                arguments={"path": "README.md"},
                description="Read the project README so the summary uses real repository content.",
            )
        if len(successful_reads) == 1:
            summary = self._summarize(successful_reads[0].output)
            return ActionProposal(
                tool="write_file",
                arguments={"path": "output/summary.md", "content": summary},
                description="Save a short deterministic summary of README.md.",
            )
        if len(successful_reads) >= 2:
            return AgentFinish(final_output="Summary saved to output/summary.md.")
        return AgentFinish(final_output="The demo task could not be planned from the available observations.")

    @staticmethod
    def _summarize(readme: str) -> str:
        lines = [line.strip() for line in readme.splitlines()]
        title = next((line.lstrip("# ").strip() for line in lines if line.startswith("# ")), "Project README")
        intro_lines: list[str] = []
        after_title = False
        for line in lines:
            if line.startswith("# ") and not after_title:
                after_title = True
                continue
            if not after_title:
                continue
            if line.startswith(("[English]", "[中文]", "![")):
                continue
            if not line:
                if intro_lines:
                    break
                continue
            if line.startswith("#") or line.startswith("```"):
                if intro_lines:
                    break
                continue
            intro_lines.append(line.replace("**", "").replace("__", ""))
            if len(" ".join(intro_lines)) >= 300:
                break
        intro = " ".join(intro_lines).strip()
        if not intro:
            intro = "This README introduces the project and its current capabilities."
        if len(intro) > 400:
            boundary = max(intro.rfind(". ", 0, 400), intro.rfind("。", 0, 400))
            intro = intro[: boundary + 1 if boundary >= 0 else 400]
        intro = intro.rstrip()
        return f"# {title} — 简短摘要\n\n{intro}\n"
