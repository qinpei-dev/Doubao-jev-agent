# Changelog

## Unreleased

### Added
- Controlled local Agent loop with deterministic policy, JEV Choice decisions, explicit review approval, one-use execution permits, sandboxed tools, and structured traces.
- FastMCP tools `controlled_agent_run` and `approve_action`, plus matching FastAPI endpoints.
- Offline control-flow tests and a real local README-to-summary demonstration.

## [0.2.1] - 2026-09-25

### Fixed
- Centralized and hardened JEV decision validation.
- Reject invalid, blank, duplicate, and unavailable decision options.
- Fixed registered `research_skill` routing.
- Improved TypeSafe response validation and error handling.

### Tests
- Expanded test coverage from 15 to 39 tests.
- Added offline TypeSafe response parsing tests.
- Added invalid-choice and validation boundary tests.

### CI
- Added GitHub Actions CI for Python 3.11, 3.12, and 3.13.
- Added pytest and mock benchmark smoke checks.

### Documentation
- Aligned README / README_CN with actual JEV capabilities and current project behavior.
- Clarified Choice as the currently integrated native primitive.
- Clarified that ranking / action gating remain application-layer abstractions.

## v0.1.0

- Positioned the project as an MCP Server exposing a JEV-powered MCP Decision Layer for MCP-compatible AI Agents, with client compatibility notes and decision routing examples.
- Integrated the TypeSafe JEV API for decisions, with a local mock when no API key is configured.
- Added an MCP server that exposes decision, skill execution, and skill discovery tools.
- Added a skill registry, router, and executor with local demonstration workflows.
- Tested with Doubao Desktop MCP Connector.
