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
