# Changelog

## Unreleased

- Validate non-blank, unique decision options and reject choices outside the caller's allowed set before routing or execution.
- Validate TypeSafe Choice response fields with offline MockTransport tests.
- Add Python 3.11–3.13 CI for pytest and the credential-free mock benchmark.
- Clarify that action gates are caller-level abstractions over Choice and keep execution caller-controlled.

## v0.1.0

- Positioned the project as an MCP Server exposing a JEV-powered MCP Decision Layer for MCP-compatible AI Agents, with client compatibility notes and decision routing examples.
- Integrated the TypeSafe JEV API for decisions, with a local mock when no API key is configured.
- Added an MCP server that exposes decision, skill execution, and skill discovery tools.
- Added a skill registry, router, and executor with local demonstration workflows.
- Tested with Doubao Desktop MCP Connector.
