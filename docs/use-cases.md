# Decision Routing Examples

## Why Decision Layer?

An Agent client may ask an LLM to choose the next action:

```text
Task
    ↓
LLM decides
    ↓
Execution
```

This project offers a separate, lightweight decision layer for structured decisions and predictable routing.

With JEV, the MCP client supplies a task and allowed choices to a separate decision layer:

```text
Task
    ↓
JEV Decision Layer
    ↓
Skill Routing
    ↓
Execution
```

JEV returns a structured choice from the supplied options. The client can use that choice to route a workflow and inspect action selection. The AI Agent remains responsible for generation and the wider workflow.

## Examples

Run from the repository root. Without `JEV_API_KEY`, each example uses the local deterministic mock. With a key, it calls the real TypeSafe JEV API, so results may differ.

- [Agent Routing](../examples/use_cases/career_decision.py) asks which skill fits a job analysis task.
- [Coding Decision](../examples/use_cases/coding_decision.py) asks which skill fits a FastAPI error.
- [Research Decision](../examples/use_cases/tool_selection.py) asks which skill fits research for a technical report.

These examples stop at the decision result. The selected `research_skill` can also run through the default Skill Executor, which returns a local mock result without retrieving external sources.

## Native JEV choices and application-level gates

TypeSafe documents three native question types: [Choice](https://docs.typesafe.ai/primitives/choice), [Score](https://docs.typesafe.ai/primitives/score), and [Noul](https://docs.typesafe.ai/primitives/noul). This repository currently integrates the Choice response (`choice`, `confidence`, and `probabilities`). Score and Noul are not exposed by its client or MCP tools.

An Agent can use `jev_decide` to ask for an application-level action gate by supplying options such as `allow`, `review`, and `deny`, with the proposed action and applicable policy in the task. That gate is a Choice-based application abstraction, not a separate TypeSafe Gate primitive. v0.3.0 adds a controlled service for a small fixed set of sandboxed local file tools; it does not execute arbitrary file, email, or shell actions. The legacy `agent_run` tool still executes only a registered local demo skill. See [Controlled Agent](controlled-agent.md) for the new execution boundary and its limits.

TypeSafe Choice includes probabilities that caller code can sort. This repository discards the full probability map and exposes the selected choice, confidence, and a locally constructed summary reason in the HTTP API; its MCP tool returns only the choice and confidence. The adapter uses the highest-probability alternative in that summary, but does not expose a ranked list. Applications that need one must sort Choice probabilities themselves; TypeSafe documents these probabilities rather than a separate ranking primitive. The API evaluates the state supplied by its caller, so any verification question must be grounded in that state; the repository does not retrieve external evidence.
