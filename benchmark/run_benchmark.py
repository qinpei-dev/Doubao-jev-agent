"""Offline routing benchmark; never loads credentials or calls a paid model."""

import asyncio
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
import platform
import statistics
import sys
from time import perf_counter_ns

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.decision import DecisionEngine  # noqa: E402
from src.jev.mock import MockJEVClient  # noqa: E402
from src.skills.executor import SkillExecutor  # noqa: E402
from src.skills.registry import create_default_registry  # noqa: E402


OPTIONS = ["career_skill", "coding_skill", "research_skill", "writing_skill"]
REPEATS = 100
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
    baseline_ms: float
    jev: str
    jev_ms: float
    confidence: float
    baseline_execution: str
    jev_execution: str


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


def estimated_llm_calls_saved(task_count: int, baseline_calls_per_task: int = 1, jev_calls_per_task: int = 0) -> int:
    """Hypothetical decision-call difference; excludes other workflow calls."""
    return task_count * (baseline_calls_per_task - jev_calls_per_task)


def execute_local(executor: SkillExecutor, skill: str, task: str) -> str:
    """Attempt the existing local demo workflow; flag unregistered choices."""
    try:
        return executor.execute(skill, task)["status"]
    except ValueError as exc:
        if str(exc).startswith("No skill registered for decision:"):
            return "unavailable"
        raise


async def measure_task(task: str, expected: str, engine: DecisionEngine, executor: SkillExecutor) -> Result:
    baseline_times = []
    jev_times = []
    for _ in range(REPEATS):
        start = perf_counter_ns()
        baseline = baseline_decide(task)
        baseline_times.append((perf_counter_ns() - start) / 1_000_000)

        start = perf_counter_ns()
        decision = await engine.decide(task, OPTIONS)
        jev_times.append((perf_counter_ns() - start) / 1_000_000)

    assert baseline in OPTIONS and decision.decision in OPTIONS
    baseline_execution = execute_local(executor, baseline, task)
    # The registry lookup is the explicit Skill Routing step in the JEV flow.
    routed = executor.registry.get(decision.decision)
    jev_execution = execute_local(executor, decision.decision, task) if routed else "unavailable"
    return Result(
        task, expected, baseline, statistics.median(baseline_times),
        decision.decision, statistics.median(jev_times), decision.confidence,
        baseline_execution, jev_execution,
    )


def render_report(results: list[Result]) -> str:
    baseline_average = statistics.mean(item.baseline_ms for item in results)
    jev_average = statistics.mean(item.jev_ms for item in results)
    baseline_matches = sum(item.baseline == item.expected for item in results)
    jev_matches = sum(item.jev == item.expected for item in results)
    unavailable = sum(item.jev_execution == "unavailable" for item in results)
    rows = [
        f"| {item.task} | {item.expected} | {item.baseline} | {item.baseline_ms:.4f} | "
        f"{item.jev} | {item.jev_ms:.4f} | {item.confidence:.0%} | {item.baseline_execution} | {item.jev_execution} |"
        for item in results
    ]
    return "\n".join([
        "# Decision Layer Benchmark",
        "",
        "## Environment",
        "",
        f"- Python: {platform.python_version()} ({platform.system()})",
        f"- MCP: mcp {version('mcp')} installed; transport and client handshake were not measured",
        "- Decision backend: local `MockJEVClient` through `DecisionEngine`; no real JEV API, API key, or paid model used",
        f"- Timing: {REPEATS} local decision calls per task; each row reports the median in milliseconds; these latencies do not represent real JEV API inference speed",
        "- Baseline: deterministic keyword selector standing in for direct Agent selection; no LLM was called",
        "- Execution: local mock demo skills, including `research_skill`; `unavailable` means the selected skill is not registered",
        "- Primary purpose: test decision routing consistency against illustrative task labels and exercise the local execution path",
        "",
        "## Results",
        "",
        "| Task | Expected | Baseline decision | Baseline latency (ms) | Mock decision | Mock latency (ms) | Confidence | Baseline execution | Mock execution |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | --- | --- |",
        *rows,
        "",
        f"- Tasks: {len(results)}; expected labels are illustrative, not a ground-truth quality evaluation.",
        f"- Average of per-task median local decision latency: baseline {baseline_average:.4f} ms; mock backend {jev_average:.4f} ms. These are Python process timings, not real JEV API inference latency.",
        f"- Matches to illustrative labels: baseline {baseline_matches}/{len(results)}; mock backend {jev_matches}/{len(results)}.",
        f"- Mock backend local execution unavailable: {unavailable}/{len(results)}.",
        "- Steps per task: baseline 2 (direct decision, execution attempt); mock backend 3 (decision, registry routing, execution attempt). These counts describe the instrumented flows, not LLM reasoning steps.",
        "",
        "## Cost Estimation",
        "",
        "`estimated_llm_calls_saved(task_count, baseline_calls_per_task=1, jev_calls_per_task=0)` is an assumption-based interface. "
        f"Under those inputs it returns {estimated_llm_calls_saved(len(results))} decision calls for {len(results)} tasks. "
        "No LLM calls, token counts, prices, or real savings were measured; the wider Agent may still call an LLM.",
        "",
        "## Analysis",
        "",
        "This benchmark primarily tests decision routing consistency with a local mock backend and illustrative labels. "
        "It does not establish real JEV API inference speed, faster decisions, lower cost, or better quality than an LLM. "
        "The mock routed `帮我定位FastAPI错误` to `writing_skill`, and its 50% confidence on `写一个技术博客` reflects a fallback rather than a matched rule. "
        "All selected example skills now complete the local mock execution path, including `research_skill`; this does not perform live research.",
        "",
        "Run `python benchmark/run_benchmark.py` from the repository root to regenerate this machine-specific report.",
        "",
    ])


async def main() -> None:
    engine = DecisionEngine(MockJEVClient())
    executor = SkillExecutor(create_default_registry())
    results = [await measure_task(task, expected, engine, executor) for task, expected in TASKS]
    path = ROOT / "benchmark" / "results.md"
    path.write_text(render_report(results), encoding="utf-8")
    print(f"Wrote {path} ({len(results)} tasks)")
    print(f"Average local mock decision latency: {statistics.mean(item.jev_ms for item in results):.4f} ms")


if __name__ == "__main__":
    asyncio.run(main())
