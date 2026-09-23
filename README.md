# Doubao JEV Agent

**A decision layer for Doubao Agent powered by JEV.**

> **LLM generates. JEV decides.**

Doubao JEV Agent is a small, extensible decision layer that routes a natural-language task to a Skill or Agent. v0.1 ships with a deterministic mock JEV engine, a provider-neutral Doubao adapter contract, and a FastAPI service. It does not call Doubao or a hosted JEV service.

## Why a decision layer?

An LLM can generate a response, but asking it to pick tools, skills, and agents anew on every turn can make orchestration hard to predict. This project puts routing behind a small decision interface: the caller supplies the task and allowed options, and the JEV client returns a constrained choice with confidence and a reason.

## Architecture

```mermaid
flowchart TD
    U[User request] --> D[Doubao Agent]
    D --> J[Doubao JEV Agent API]
    J --> E[JEV Decision Layer]
    E --> R[Skill / Agent Router]
    R --> T[Tools / Agents]
```

The JEV boundary is asynchronous and replaceable. Mock mode works without credentials. An optional generic HTTP client is available in real mode; configure its endpoint and key using the environment variables below. The endpoint must accept `{ "task": "...", "options": [...] }` and return `{ "decision": "...", "confidence": 0.9, "reason": "..." }`.

## Quick Start

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```

Open `http://127.0.0.1:8000/docs`. Try a route:

```bash
curl -X POST http://127.0.0.1:8000/route/skill \
  -H 'Content-Type: application/json' \
  -d '{"task":"帮我优化论文格式"}'
```

Response:

```json
{"skill":"paper_skill","confidence":0.94,"reason":"task requires paper or document formatting"}
```

## Demos

Run from the project root:

```bash
python -m examples.skill_router_demo
python -m examples.doubao_demo
python -m examples.agent_router_demo
```

The demos cover paper skill routing, career skill routing, and GitHub issue to coding-agent routing. Each prints the task, selected destination, confidence, and reason for easy terminal screenshots.

## API

- `GET /health` — service health
- `POST /decide` — choose among caller-provided options (`task`, `options`)
- `POST /route/skill` — route a task to a built-in skill
- `POST /route/agent` — route a task to an agent

## Docker

```bash
docker compose up --build
```

The API is then available at `http://localhost:8000`. Mock mode is the default and requires no API key.

To use a compatible JEV endpoint, set `JEV_MODE=real`, `JEV_API_URL`, and `JEV_API_KEY`. The endpoint contract is generic and must be supplied by your JEV deployment; this project does not claim an official JEV API contract.

## Tests

```bash
pytest
```

## Roadmap

### v0.1

- Basic decision router
- Doubao skill routing
- Mock JEV engine
- FastAPI service and Docker packaging

### Future

- Real JEV API integration
- MCP support
- More Doubao Agent integrations
- Multi-agent workflows

## Scope

This is an early open-source MVP. It has no frontend, database, user system, SaaS layer, or real Doubao API binding. The adapter and JEV client interfaces are extension points, not claims of provider integration.

## License

MIT
