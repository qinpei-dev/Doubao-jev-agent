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

See [Doubao Desktop MCP Setup](doubao-mcp.md) for local configuration.

## Antigravity

**Status:** Tested

Validated:

- STDIO transport
- Tool discovery
- Real TypeSafe JEV API call

In both clients, the MCP client only communicates with the local MCP server. Configure the JEV API key in the MCP server environment, not in a shared client configuration.
