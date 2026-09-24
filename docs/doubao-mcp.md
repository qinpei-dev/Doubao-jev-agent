# Doubao Desktop MCP Setup

## Prerequisites

- Install Python 3.11 or later and clone this repository.
- From the repository root, create and activate a virtual environment, then run `pip install -r requirements.txt`.
- Have a Doubao Desktop version that supports custom MCP connectors. The exact menu labels may vary by version.

## Add the connector in Doubao Desktop

1. Open Doubao Desktop.
2. Open **Skills** (技能), then **Connectors** (连接器).
3. Choose **Create custom MCP** (创建自定义 MCP).
4. Select **STDIO** as the transport and enter:

   ```text
   command: python
   args:
     - -m
     - src.mcp.server
   ```

5. Set the working directory to the absolute path of your cloned repository. For example, on Windows:

   ```text
   D:\projects\Doubao-jev-agent
   ```

   Python must start in this directory so it can import `src`. Select the `python` executable from the virtual environment if Doubao Desktop does not inherit your activated environment.
6. Save the connector and check that the `jev_decide`, `agent_run`, `list_skills`, `controlled_agent_run`, and `approve_action` tools appear. The controlled tools are new in the v0.3 development branch; the earlier client validation covered the first three tools.

The equivalent MCP server configuration is:

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

You can start from [`mcp.json.example`](../mcp.json.example) if your connector accepts a JSON configuration. Set the connector's working directory separately when its configuration format requires that.

## Use your own JEV API key

The server uses a local mock when `JEV_API_KEY` is unset. To call the real TypeSafe JEV API, obtain your own key and set `JEV_API_KEY` in the server process environment or in a private `.env` file in the repository root:

```dotenv
JEV_API_KEY=your_own_key
```

Do not commit `.env` or share an MCP configuration containing your key. See the [Security Policy](../SECURITY.md).
