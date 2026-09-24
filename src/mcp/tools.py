"""MCP tool registration backed by the existing JEV and skill components."""
from mcp.server.fastmcp import FastMCP
from pathlib import Path

from ..agent import ControlledAgentRunner, DeterministicDemoAgent
from ..core.decision import DecisionEngine
from ..jev.client import JEVClient
from ..skills import SkillExecutor, SkillRegistry, create_default_registry
from .schemas import AgentRunDecision, AgentRunInput, AgentRunOutput, JEVDecideInput, JEVDecision


def register_tools(
    server: FastMCP,
    engine: DecisionEngine,
    registry: SkillRegistry | None = None,
    controlled_agent: ControlledAgentRunner | None = None,
) -> None:
    registry = registry or create_default_registry()
    executor = SkillExecutor(registry)
    controlled_agent = controlled_agent or ControlledAgentRunner(
        engine, Path.cwd(), DeterministicDemoAgent()
    )

    @server.tool()
    async def jev_decide(task: str, options: list[str]) -> dict:
        """Make a constrained decision with the JEV Decision Engine."""
        request = JEVDecideInput(task=task, options=options)
        decision = await engine.decide(request.task, request.options)
        if decision.decision not in request.options:
            raise ValueError("Decision engine returned an unavailable option")
        return JEVDecision(decision=decision.decision, confidence=decision.confidence).model_dump()

    @server.tool()
    async def agent_run(task: str) -> dict:
        """Run JEV skill selection followed by local Skill Executor execution."""
        request = AgentRunInput(task=task)
        decision = await engine.decide(request.task, [skill.name for skill in registry.list()])
        execution = executor.execute(decision, request.task)
        return AgentRunOutput(
            decision=AgentRunDecision(skill=decision.decision, confidence=decision.confidence),
            execution=execution,
        ).model_dump()

    @server.tool()
    def list_skills() -> list[str]:
        """List skill names supported by this Doubao JEV Agent instance."""
        return [skill.name for skill in registry.list()]

    @server.tool()
    async def controlled_agent_run(task: str, max_steps: int = 5) -> dict:
        """Run proposed local actions through policy, JEV, permits, and sandbox tools."""
        trace = await controlled_agent.run(task, max_steps=max_steps)
        return trace.model_dump(mode="json")

    @server.tool()
    async def approve_action(action_id: str) -> dict:
        """Approve and resume one action currently waiting for caller review."""
        trace = await controlled_agent.approve_action(action_id)
        return trace.model_dump(mode="json")


def create_mcp_server(
    client: JEVClient | None = None,
    sandbox_root: str | Path | None = None,
) -> FastMCP:
    """Create the MCP server, defaulting to the environment-selected JEV client."""
    from ..jev.client import JEVClient as ClientFactory

    server = FastMCP("doubao-jev-agent")
    engine = DecisionEngine(client or ClientFactory.from_env())
    controlled_agent = ControlledAgentRunner(
        engine, sandbox_root or Path.cwd(), DeterministicDemoAgent()
    )
    register_tools(server, engine, controlled_agent=controlled_agent)
    return server
