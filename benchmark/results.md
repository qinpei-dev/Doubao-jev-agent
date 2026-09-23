# Decision Layer Benchmark

## Environment

- Python: 3.13.7 (Windows)
- MCP: mcp 1.30.0 installed; transport and client handshake were not measured
- JEV: local `MockJEVClient` through `DecisionEngine`; no API key or paid model used
- Timing: 100 decision calls per task; each row reports the median in milliseconds; local machine only
- Baseline: deterministic keyword selector standing in for direct Agent selection; no LLM was called
- Execution: existing local demo skills only; `unavailable` means the selected skill is not registered

## Results

| Task | Expected | Baseline decision | Baseline latency (ms) | JEV decision | JEV latency (ms) | Confidence | Baseline execution | JEV execution |
| --- | --- | --- | ---: | --- | ---: | ---: | --- | --- |
| 帮我分析一个AI实习岗位 | career_skill | career_skill | 0.0006 | career_skill | 0.0070 | 91% | completed | completed |
| 分析这个招聘岗位是否适合我 | career_skill | career_skill | 0.0005 | career_skill | 0.0067 | 91% | completed | completed |
| 帮我定位FastAPI错误 | coding_skill | coding_skill | 0.0013 | writing_skill | 0.0067 | 50% | completed | completed |
| 排查Python代码报错 | coding_skill | coding_skill | 0.0015 | coding_skill | 0.0067 | 91% | completed | completed |
| 调研RAG最新方案 | research_skill | research_skill | 0.0021 | research_skill | 0.0066 | 91% | unavailable | unavailable |
| 调研向量数据库选型 | research_skill | research_skill | 0.0021 | research_skill | 0.0067 | 91% | unavailable | unavailable |
| 写一个技术博客 | writing_skill | writing_skill | 0.0025 | writing_skill | 0.0065 | 50% | completed | completed |
| 润色一篇技术文章 | writing_skill | writing_skill | 0.0026 | writing_skill | 0.0067 | 91% | completed | completed |
| 搜索资料并整理报告 | research_skill | research_skill | 0.0022 | research_skill | 0.0067 | 91% | unavailable | unavailable |
| 搜索资料并生成技术报告 | research_skill | research_skill | 0.0023 | research_skill | 0.0067 | 91% | unavailable | unavailable |

- Tasks: 10; expected labels are illustrative, not a ground-truth quality evaluation.
- Average of per-task median decision latency: baseline 0.0018 ms; JEV 0.0067 ms.
- Matches to illustrative labels: baseline 10/10; JEV 9/10.
- JEV local execution unavailable: 4/10 (the default registry has no `research_skill`).
- Steps per task: baseline 2 (direct decision, execution attempt); JEV 3 (decision, registry routing, execution attempt). These counts describe the instrumented flows, not LLM reasoning steps.

## Cost Estimation

`estimated_llm_calls_saved(task_count, baseline_calls_per_task=1, jev_calls_per_task=0)` is an assumption-based interface. Under those inputs it returns 10 decision calls for 10 tasks. No LLM calls, token counts, prices, or real savings were measured; the wider Agent may still call an LLM.

## Analysis

JEV Decision Layer focuses on structured routing, predictable decisions, and reducing unnecessary agent execution where the workflow allows it. This run measures local mock routing only. It does not establish faster decisions, lower cost, or better quality than an LLM. The mock routed `帮我定位FastAPI错误` to `writing_skill`, and its 50% confidence on `写一个技术博客` reflects a fallback rather than a matched rule. The unregistered research choice also shows that a decision alone does not guarantee execution.

Run `python benchmark/run_benchmark.py` from the repository root to regenerate this machine-specific report.
