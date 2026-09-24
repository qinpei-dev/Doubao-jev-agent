# MCP Client Compatibility

The MCP client communicates with the local MCP server over stdio. The MCP server reads `JEV_API_KEY` from its own environment (or a private `.env` file) and makes the TypeSafe JEV API request. The client does not need the JEV API key.

## Doubao Desktop

**Status:** Tested

Validated:

- MCP handshake
- Tool discovery
- Real JEV API call

Discovered tools:

- `jev_decide`
- `agent_run`
- `list_skills`

These client-side checks covered the v0.2.1 tools. The v0.3 development branch adds `controlled_agent_run` and `approve_action`; these new tools have automated FastMCP coverage but have not yet been manually validated in Doubao Desktop or Antigravity.

See [Doubao Desktop MCP Setup](doubao-mcp.md) for local configuration.

## Antigravity

**Status:** Tested

Validated:

- STDIO transport
- Tool discovery
- Real TypeSafe JEV API call

In both clients, the MCP client only communicates with the local MCP server. Configure the JEV API key in the MCP server environment, not in a shared client configuration.
