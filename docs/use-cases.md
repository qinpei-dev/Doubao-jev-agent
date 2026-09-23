# Use Cases

## Why Decision Layer?

A traditional Agent may ask an LLM to choose every next action:

```text
User Task
    ↓
LLM decides everything
    ↓
Tool execution
```

Depending on the workflow, this can lead to unstable tool selection, unnecessary model calls, and higher execution cost.

With JEV, the MCP client supplies a task and allowed choices to a separate decision layer:

```text
User Task
    ↓
JEV Decision
    ↓
Skill Routing
    ↓
Execution
```

JEV returns a structured choice from the supplied options. The client can use that choice to route a workflow, making action selection easier to inspect and potentially more predictable. A smaller decision step may reduce routing cost in suitable workflows, but cost savings and decision quality depend on the task, model calls, and deployment. An AI Agent remains responsible for the wider workflow.

## Examples

Run from the repository root. Without `JEV_API_KEY`, each example uses the local deterministic mock. With a key, it calls the real TypeSafe JEV API, so results may differ.

- [Agent Routing](../examples/use_cases/career_decision.py) asks which skill fits a job analysis task.
- [Coding Decision](../examples/use_cases/coding_decision.py) asks which skill fits a FastAPI error.
- [Research Decision](../examples/use_cases/tool_selection.py) asks which skill fits research for a technical report.

These examples stop at the decision result. The selected `research_skill` can also run through the default Skill Executor, which returns a local mock result without retrieving external sources.
