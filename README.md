# Doubao-JEV-Agent

[English](README.md) | [中文](README_CN.md)

**A JEV-powered decision layer exposed through MCP for MCP-compatible AI Agents.**

This project provides a lightweight decision layer between AI clients and execution workflows.

Originally built for Doubao MCP integration, now supports MCP-compatible clients.

Doubao-JEV-Agent is an MCP Server for Agent clients and Agent workflows. An MCP-compatible AI Agent supplies a task and allowed choices; JEV selects from those options, and the local executor runs the selected skill. The client remains responsible for the wider Agent workflow.

The v0.3.0 development branch adds an optional controlled execution loop. JEV does not execute tools or replace the Agent; it sits at the decision boundary between an action proposal and local tool execution.

```mermaid
flowchart TD
    C[MCP Client] --> A[Agent Planner]
    A --> P[Action Proposal]
    P --> D[Deterministic Policy]
    D --> J[JEV Choice]
    J --> O{ALLOW / REVIEW / DENY}
    O -->|allow| X[One-use Execution Permit]
    O -->|review| H[Wait for explicit caller approval]
    O -->|deny| B[Blocked]
    H --> X
    X --> T[Sandbox Tool Executor]
    T --> R[Observation]
    R --> A
```

`allow`, `review`, and `deny` are this project's application-layer interpretation of the TypeSafe Choice result. They are not a separate TypeSafe Gate primitive. The legacy `agent_run` skill workflow remains available; use `controlled_agent_run` for the permit-gated local tools. See [Controlled Agent](docs/controlled-agent.md) for its sandbox and limits.

## Demo

![Doubao MCP demo showing the jev_decide tool call and decision result](docs/images/doubao-mcp-demo.png)

Tested MCP Clients:

- Doubao Desktop MCP Connector
- Antigravity MCP Client

Real MCP call → Real TypeSafe JEV API → Decision result.

Run a decision and local skill execution from the repository root:

```bash
python -m examples.agent_run_demo
```

In mock mode, the example selects `career_skill` and shows the executor result:

```text
JEV: career_skill (91.00%)
Executor: career_skill.execute()
结果: Career analysis workflow executed
```

No API key is needed for this demo. With `JEV_API_KEY` set, it calls the real TypeSafe JEV API and the decision may differ.

Run the new file-execution loop from the repository root:

```bash
python -m examples.controlled_agent_demo --approve-existing
```

The deterministic demo reads the actual `README.md`, writes `output/summary.md` inside the configured sandbox, and prints a structured trace. It uses the local JEV mock by default and stays offline; pass `--real-jev` to use the configured `JEV_API_KEY`. This checkout already tracks `output/summary.md`, so the example passes `--approve-existing` as explicit approval for that known overwrite. Without the flag, the action waits for review. The tool execution itself is real.

## Features

- Exposes JEV decisions, skill execution, and skill discovery as MCP tools.
- Adds a permit-gated controlled Agent loop with local sandbox file tools, explicit review, and a machine-readable trace.
- Uses the TypeSafe JEV API when `JEV_API_KEY` is configured and validates that each returned choice is allowed.
- Uses a deterministic local mock without a key, so the project can be tried without external credentials.
- Includes a FastAPI service, Docker packaging, and demo scripts alongside the MCP server.
- Provides an extensible skill registry and executor.

The included career, paper, coding, research, and writing skills are simulated workflows. They demonstrate routing and execution; they do not call external services or perform the described work themselves. The Doubao adapter is an extension contract, not a live Doubao API integration.

## Why Decision Layer?

Modern AI Agents often rely on LLMs for both generation and decision making. This project separates decision making into a dedicated, lightweight decision layer for structured decisions and predictable routing.

Without Decision Layer:

```text
Task
  ↓
LLM decides
  ↓
Execution
```

With JEV:

```text
Task
  ↓
JEV Decision Layer
  ↓
Skill Routing
  ↓
Execution
```

The MCP client provides the task and allowed choices. JEV returns a choice that is checked against those options before routing. LLMs can still generate content and manage the wider Agent workflow. See [Decision Routing Examples](docs/use-cases.md) for examples and limits.

## Architecture

![Doubao-JEV-Agent architecture diagram](docs/images/architecture.png)

MCP handles communication. JEV makes a structured decision from the client's allowed choices. The Skill Router selects the registered skill, and the executor runs its local workflow.

## Quick Start

Requires Python 3.11 or later.

```bash
git clone https://github.com/qinpei-dev/Doubao-jev-agent.git
cd Doubao-jev-agent
python -m venv .venv
```

Activate the environment and install dependencies:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Run `python -m examples.agent_run_demo` to try the mock workflow, or start the HTTP API:

```bash
uvicorn src.main:app --reload
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for interactive API documentation. The service starts in mock mode unless a JEV key is configured.

## MCP

MCP (Model Context Protocol) provides a standard way for AI clients to connect with external tools and services. This MCP server exposes `jev_decide`, `agent_run`, `list_skills`, `controlled_agent_run`, and `approve_action`.

Install the dependencies, then add the following server entry to your MCP host configuration. Start the host with the repository root as its working directory so Python can import `src`.

```json
{
  "mcpServers": {
    "doubao-jev-agent": {
      "command": "python",
      "args": ["-m", "src.mcp.server"],
      "env": {}
    }
  }
}
```

You can also copy [`mcp.json.example`](mcp.json.example) as a starting point. For desktop setup steps, see [Doubao MCP Setup](docs/doubao-mcp.md). The MCP server uses stdio transport and provides:

| Tool | Purpose |
| --- | --- |
| `jev_decide` | Choose from caller-provided options using JEV. |
| `agent_run` | Select a registered skill, execute it, and return the decision and result. |
| `list_skills` | List the skills registered on this server. |
| `controlled_agent_run` | Run local file actions through deterministic policy, JEV Choice, permits, and the sandbox executor. |
| `approve_action` | Approve and resume one action returned with `approval_required`. |

The v0.2.1 MCP connector was tested with Doubao Desktop and Antigravity. The new controlled tools have automated FastMCP coverage but have not yet been manually validated in those clients. See [MCP Client Compatibility](docs/mcp-clients.md) for details. Each user runs their own local MCP server; this project does not provide a shared remote MCP service or JEV quota.

### Use the real JEV API

Request your own JEV API key through [TypeSafe](https://typesafe.ai/). Set it in the server process environment or in a private, untracked `.env` file in the repository root:

```dotenv
JEV_API_KEY=your_own_key
```

Then run the MCP server with `python -m src.mcp.server`, or run the real API demo:

```bash
python -m examples.real_jev_demo
```

Without a key, both use the local mock. With a key, requests go directly from your machine to TypeSafe over HTTPS using your account and quota. Never commit your `.env` file or put a key in an MCP configuration that you share.

## Examples

Run these commands from the repository root:

```bash
python -m examples.skill_router_demo
python -m examples.doubao_demo
python -m examples.agent_router_demo
python -m examples.agent_run_demo
python -m examples.real_jev_demo
```

The demos use the local mock by default. `agent_run_demo` and `real_jev_demo` use TypeSafe JEV when `JEV_API_KEY` is set. No demo includes a bundled API key or project-provided quota.

## Decision Routing Examples

The routing flow is **Task → JEV Decision → Selected Skill → Execution Path**. These examples show the decision step using the environment-selected JEV client; they stop at the choice rather than executing a skill. With no `JEV_API_KEY`, the local mock provides a deterministic demonstration; with a key, the choice comes from the real TypeSafe JEV API and may differ. Run from the repository root:

- [Agent Routing](examples/use_cases/career_decision.py): `python -m examples.use_cases.career_decision`
- [Coding Decision](examples/use_cases/coding_decision.py): `python -m examples.use_cases.coding_decision`
- [Research Decision](examples/use_cases/tool_selection.py): `python -m examples.use_cases.tool_selection`

For the reasoning behind these examples, read [Decision Routing Examples](docs/use-cases.md).

### HTTP API example

With the API running locally, send a task:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"task":"帮我分析这个招聘岗位"}'
```

In mock mode, the response contains the selected skill and execution result. The service also provides:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check service health. |
| `POST` | `/decide` | Choose from caller-provided options. |
| `POST` | `/route/skill` | Route a task to a built-in skill. |
| `POST` | `/route/agent` | Route a task to an agent. |
| `POST` | `/api/v1/agent/run` | Decide a skill and execute its workflow. |
| `POST` | `/api/v1/controlled-agent/run` | Run actions through the controlled execution loop and return a trace. |
| `POST` | `/api/v1/controlled-agent/{run_id}/approve` | Approve the matching action waiting for review. |

## Decision Routing Evaluation

See the [Decision Routing Evaluation](benchmark/results.md). Run `python benchmark/run_benchmark.py` to regenerate it locally. The 10 example tasks test the decision routing flow, example task matching, confidence, and local demo execution for career, coding, research, and writing skills. The decision backend is a deterministic local mock; its latency does not represent real API latency or LLM generation speed. The evaluation makes no performance or cost claim. No paid model or external research service is called.

## Roadmap

The latest published release is [v0.2.1](https://github.com/qinpei-dev/Doubao-jev-agent/releases/tag/v0.2.1). It provides the MCP decision layer, local demo workflows, an HTTP API, and offline decision-routing evaluation. Possible future work includes more MCP host examples; no delivery dates are committed.

## Docker

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`. Docker Compose binds the host port to `127.0.0.1`; mock mode is the default.

## Security and deployment

- Use your own JEV API key. The project has no shared credentials or quota.
- Keep `.env` and any MCP host configuration containing a key private.
- The HTTP API has no authentication. Keep it on a trusted local interface when using a real key; the included Compose configuration binds it to localhost.
- Real JEV requests go directly from your server to `https://api.typesafe.ai/v1/systemone` over HTTPS.

## Contributing

Run `python -m pytest` before submitting changes. See [CONTRIBUTING.md](CONTRIBUTING.md) for the skill extension steps and contribution ideas.

## Extending Skills

Developers can extend the server's local skill registry by adding a `BaseSkill` subclass with a `name`, `description`, and `execute(input)` method, then registering an instance with `SkillRegistry`. See the runnable [Custom Skill Example](examples/custom_skill.py). To make a new skill available to the default MCP server, add it to `create_default_registry()` as described in [CONTRIBUTING.md](CONTRIBUTING.md).

See the [Security Policy](SECURITY.md) for vulnerability reporting and credential guidance.

## License

Distributed under the [MIT License](LICENSE).
