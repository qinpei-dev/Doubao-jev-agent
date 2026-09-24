"""MCP tool registration backed by the existing JEV and skill components."""
from mcp.server.fastmcp import FastMCP

from ..core.decision import DecisionEngine
from ..jev.client import JEVClient
from ..skills import SkillExecutor, SkillRegistry, create_default_registry
from .schemas import AgentRunDecision, AgentRunInput, AgentRunOutput, JEVDecideInput, JEVDecision


def register_tools(
    server: FastMCP,
    engine: DecisionEngine,
    registry: SkillRegistry | None = None,
) -> None:
    registry = registry or create_default_registry()
    executor = SkillExecutor(registry)

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


def create_mcp_server(client: JEVClient | None = None) -> FastMCP:
    """Create the MCP server, defaulting to the environment-selected JEV client."""
    from ..jev.client import JEVClient as ClientFactory

    server = FastMCP("doubao-jev-agent")
    register_tools(server, DecisionEngine(client or ClientFactory.from_env()))
    return server
