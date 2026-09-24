"""Run the PermitMCP MCP server over stdio."""
from .tools import create_mcp_server

mcp = create_mcp_server()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
