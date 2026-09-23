# Decision Routing Evaluation

## Scope

- This 10-task evaluation exercises the decision routing flow: task → mock decision engine → registered skill → local demo execution.
- Expected labels are illustrative example task matching criteria, not verified ground truth or a measure of general decision quality.
- The baseline is a deterministic keyword selector for direct selection; it is not an LLM or a measured Agent.
- The decision backend is local `MockJEVClient` through `DecisionEngine`; no real JEV API, API key, paid model, or external research service is used.
- Mock engine latency does not represent real API latency or LLM generation speed. This evaluation makes no timing or cost claim.

## Environment

- Python: 3.13.7 (Windows)
- MCP: mcp 1.30.0 installed; transport and client handshake were not evaluated
- Execution: local demo skills; `unavailable` means the selected skill is not registered

## Results

| Task | Example label | Baseline route | Mock route | Routing match | Confidence | Baseline execution | Mock execution |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| 帮我分析一个AI实习岗位 | career_skill | career_skill | career_skill | match | 91% | completed | completed |
| 分析这个招聘岗位是否适合我 | career_skill | career_skill | career_skill | match | 91% | completed | completed |
| 帮我定位FastAPI错误 | coding_skill | coding_skill | writing_skill | mismatch | 50% | completed | completed |
| 排查Python代码报错 | coding_skill | coding_skill | coding_skill | match | 91% | completed | completed |
| 调研RAG最新方案 | research_skill | research_skill | research_skill | match | 91% | completed | completed |
| 调研向量数据库选型 | research_skill | research_skill | research_skill | match | 91% | completed | completed |
| 写一个技术博客 | writing_skill | writing_skill | writing_skill | match | 50% | completed | completed |
| 润色一篇技术文章 | writing_skill | writing_skill | writing_skill | match | 91% | completed | completed |
| 搜索资料并整理报告 | research_skill | research_skill | research_skill | match | 91% | completed | completed |
| 搜索资料并生成技术报告 | research_skill | research_skill | research_skill | match | 91% | completed | completed |

- Tasks evaluated: 10.
- Example task matching: baseline 10/10; mock route 9/10.
- Mock route local execution unavailable: 0/10.
- Routing consistency here describes agreement with these example labels only; the tasks were run once each with a deterministic mock.

## Analysis

The mock routes `帮我定位FastAPI错误` to `writing_skill`, which differs from its `coding_skill` example label. Both that task and `写一个技术博客` have 50% confidence because no mock rule matched. Career, coding, research, and writing routes all complete the local demo flow. The `research_skill` executor returns a mock result and does not retrieve sources.

Run `python benchmark/run_benchmark.py` from the repository root to regenerate this report.
