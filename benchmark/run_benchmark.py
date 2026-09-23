"""Offline decision routing evaluation; no credentials or external calls."""

import asyncio
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.decision import DecisionEngine  # noqa: E402
from src.jev.mock import MockJEVClient  # noqa: E402
from src.skills.executor import SkillExecutor  # noqa: E402
from src.skills.registry import create_default_registry  # noqa: E402


OPTIONS = ["career_skill", "coding_skill", "research_skill", "writing_skill"]
TASKS = [
    ("帮我分析一个AI实习岗位", "career_skill"),
    ("分析这个招聘岗位是否适合我", "career_skill"),
    ("帮我定位FastAPI错误", "coding_skill"),
    ("排查Python代码报错", "coding_skill"),
    ("调研RAG最新方案", "research_skill"),
    ("调研向量数据库选型", "research_skill"),
    ("写一个技术博客", "writing_skill"),
    ("润色一篇技术文章", "writing_skill"),
    ("搜索资料并整理报告", "research_skill"),
    ("搜索资料并生成技术报告", "research_skill"),
]


@dataclass
class Result:
    task: str
    expected: str
    baseline: str
    mock: str
    confidence: float
    baseline_execution: str
    mock_execution: str


def baseline_decide(task: str) -> str:
    """Deterministic direct-selection proxy, not an LLM or measured Agent."""
    if any(term in task for term in ("岗位", "实习", "招聘")):
        return "career_skill"
    if any(term in task.casefold() for term in ("fastapi", "python", "代码", "报错")):
        return "coding_skill"
    if any(term in task for term in ("调研", "搜索资料")):
        return "research_skill"
    if any(term in task for term in ("博客", "润色", "文章")):
        return "writing_skill"
    return OPTIONS[0]


def execute_local(executor: SkillExecutor, skill: str, task: str) -> str:
    """Run the registered local demo workflow."""
    try:
        return executor.execute(skill, task)["status"]
    except ValueError as exc:
        if str(exc).startswith("No skill registered for decision:"):
            return "unavailable"
        raise


async def evaluate_task(task: str, expected: str, engine: DecisionEngine, executor: SkillExecutor) -> Result:
    baseline = baseline_decide(task)
    decision = await engine.decide(task, OPTIONS)
    assert baseline in OPTIONS and decision.decision in OPTIONS
    return Result(
        task=task,
        expected=expected,
        baseline=baseline,
        mock=decision.decision,
        confidence=decision.confidence,
        baseline_execution=execute_local(executor, baseline, task),
        mock_execution=execute_local(executor, decision.decision, task),
    )


def render_report(results: list[Result]) -> str:
    baseline_matches = sum(item.baseline == item.expected for item in results)
    mock_matches = sum(item.mock == item.expected for item in results)
    unavailable = sum(item.mock_execution == "unavailable" for item in results)
    rows = [
        f"| {item.task} | {item.expected} | {item.baseline} | {item.mock} | "
        f"{'match' if item.mock == item.expected else 'mismatch'} | {item.confidence:.0%} | "
        f"{item.baseline_execution} | {item.mock_execution} |"
        for item in results
    ]
    return "\n".join([
        "# Decision Routing Evaluation",
        "",
        "## Scope",
        "",
        "- This 10-task evaluation exercises the decision routing flow: task → mock decision engine → registered skill → local demo execution.",
        "- Expected labels are illustrative example task matching criteria, not verified ground truth or a measure of general decision quality.",
        "- The baseline is a deterministic keyword selector for direct selection; it is not an LLM or a measured Agent.",
        "- The decision backend is local `MockJEVClient` through `DecisionEngine`; no real JEV API, API key, paid model, or external research service is used.",
        "- Mock engine latency does not represent real API latency or LLM generation speed. This evaluation makes no timing or cost claim.",
        "",
        "## Environment",
        "",
        f"- Python: {platform.python_version()} ({platform.system()})",
        f"- MCP: mcp {version('mcp')} installed; transport and client handshake were not evaluated",
        "- Execution: local demo skills; `unavailable` means the selected skill is not registered",
        "",
        "## Results",
        "",
        "| Task | Example label | Baseline route | Mock route | Routing match | Confidence | Baseline execution | Mock execution |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- |",
        *rows,
        "",
        f"- Tasks evaluated: {len(results)}.",
        f"- Example task matching: baseline {baseline_matches}/{len(results)}; mock route {mock_matches}/{len(results)}.",
        f"- Mock route local execution unavailable: {unavailable}/{len(results)}.",
        "- Routing consistency here describes agreement with these example labels only; the tasks were run once each with a deterministic mock.",
        "",
        "## Analysis",
        "",
        "The mock routes `帮我定位FastAPI错误` to `writing_skill`, which differs from its `coding_skill` example label. "
        "Both that task and `写一个技术博客` have 50% confidence because no mock rule matched. "
        "Career, coding, research, and writing routes all complete the local demo flow. "
        "The `research_skill` executor returns a mock result and does not retrieve sources.",
        "",
        "Run `python benchmark/run_benchmark.py` from the repository root to regenerate this report.",
        "",
    ])


async def main() -> None:
    engine = DecisionEngine(MockJEVClient())
    executor = SkillExecutor(create_default_registry())
    results = [await evaluate_task(task, expected, engine, executor) for task, expected in TASKS]
    path = ROOT / "benchmark" / "results.md"
    path.write_text(render_report(results), encoding="utf-8")
    print(f"Wrote {path} ({len(results)} tasks)")
    print(f"Example task matching: {sum(item.mock == item.expected for item in results)}/{len(results)} mock routes")


if __name__ == "__main__":
    asyncio.run(main())
