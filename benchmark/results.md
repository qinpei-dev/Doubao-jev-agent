# Decision Layer Benchmark

## Environment

- Python: 3.13.7 (Windows)
- MCP: mcp 1.30.0 installed; transport and client handshake were not measured
- Decision backend: local `MockJEVClient` through `DecisionEngine`; no real JEV API, API key, or paid model used
- Timing: 100 local decision calls per task; each row reports the median in milliseconds; these latencies do not represent real JEV API inference speed
- Baseline: deterministic keyword selector standing in for direct Agent selection; no LLM was called
- Execution: local mock demo skills, including `research_skill`; `unavailable` means the selected skill is not registered
- Primary purpose: test decision routing consistency against illustrative task labels and exercise the local execution path

## Results

| Task | Expected | Baseline decision | Baseline latency (ms) | Mock decision | Mock latency (ms) | Confidence | Baseline execution | Mock execution |
| --- | --- | --- | ---: | --- | ---: | ---: | --- | --- |
| 帮我分析一个AI实习岗位 | career_skill | career_skill | 0.0005 | career_skill | 0.0062 | 91% | completed | completed |
| 分析这个招聘岗位是否适合我 | career_skill | career_skill | 0.0005 | career_skill | 0.0062 | 91% | completed | completed |
| 帮我定位FastAPI错误 | coding_skill | coding_skill | 0.0012 | writing_skill | 0.0062 | 50% | completed | completed |
| 排查Python代码报错 | coding_skill | coding_skill | 0.0014 | coding_skill | 0.0064 | 91% | completed | completed |
| 调研RAG最新方案 | research_skill | research_skill | 0.0020 | research_skill | 0.0062 | 91% | completed | completed |
| 调研向量数据库选型 | research_skill | research_skill | 0.0020 | research_skill | 0.0062 | 91% | completed | completed |
| 写一个技术博客 | writing_skill | writing_skill | 0.0023 | writing_skill | 0.0061 | 50% | completed | completed |
| 润色一篇技术文章 | writing_skill | writing_skill | 0.0024 | writing_skill | 0.0063 | 91% | completed | completed |
| 搜索资料并整理报告 | research_skill | research_skill | 0.0021 | research_skill | 0.0062 | 91% | completed | completed |
| 搜索资料并生成技术报告 | research_skill | research_skill | 0.0021 | research_skill | 0.0062 | 91% | completed | completed |

- Tasks: 10; expected labels are illustrative, not a ground-truth quality evaluation.
- Average of per-task median local decision latency: baseline 0.0016 ms; mock backend 0.0062 ms. These are Python process timings, not real JEV API inference latency.
- Matches to illustrative labels: baseline 10/10; mock backend 9/10.
- Mock backend local execution unavailable: 0/10.
- Steps per task: baseline 2 (direct decision, execution attempt); mock backend 3 (decision, registry routing, execution attempt). These counts describe the instrumented flows, not LLM reasoning steps.

## Cost Estimation

`estimated_llm_calls_saved(task_count, baseline_calls_per_task=1, jev_calls_per_task=0)` is an assumption-based interface. Under those inputs it returns 10 decision calls for 10 tasks. No LLM calls, token counts, prices, or real savings were measured; the wider Agent may still call an LLM.

## Analysis

This benchmark primarily tests decision routing consistency with a local mock backend and illustrative labels. It does not establish real JEV API inference speed, faster decisions, lower cost, or better quality than an LLM. The mock routed `帮我定位FastAPI错误` to `writing_skill`, and its 50% confidence on `写一个技术博客` reflects a fallback rather than a matched rule. All selected example skills now complete the local mock execution path, including `research_skill`; this does not perform live research.

Run `python benchmark/run_benchmark.py` from the repository root to regenerate this machine-specific report.
