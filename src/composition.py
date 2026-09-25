"""Shared construction for the local controlled-agent adapters."""

from pathlib import Path

from .agent import ControlledAgentRunner, DeterministicDemoAgent
from .core.decision import DecisionEngine
from .jev.mock import MockJEVClient


def create_controlled_agent(
    engine: DecisionEngine, sandbox_root: str | Path | None = None
) -> ControlledAgentRunner:
    # The legacy offline mock only routes skill names. It is not a control provider.
    provider = None if isinstance(engine.client, MockJEVClient) else engine
    return ControlledAgentRunner(provider, sandbox_root or Path.cwd(), DeterministicDemoAgent())
