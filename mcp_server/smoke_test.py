"""Tiny MCP client that exercises the lakehouse server over stdio.

It does exactly what Claude Desktop would do: launch the server as a child
process, perform the MCP handshake, list the tools, and call two of them.
If this passes, connecting Claude Desktop is just a config-file step.

Usage:
    python mcp_server/smoke_test.py              # test server_solution.py
    python mcp_server/smoke_test.py server.py    # test your live-coded version
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

SERVER_FILE = Path(__file__).resolve().parent / (
    sys.argv[1] if len(sys.argv) > 1 else "server_solution.py"
)


def text_of(result: types.CallToolResult) -> str:
    block = result.content[0]
    return block.text if isinstance(block, types.TextContent) else str(block)


def show(label: str, result: types.CallToolResult) -> bool:
    """Print a tool result; return True when the call succeeded."""
    print(f"\n{label}")
    body = text_of(result)
    print("    " + body.replace("\n", "\n    "))
    if result.isError:
        print("    ^^ the tool returned an error — finish the TODOs and retry!")
    return not result.isError


async def main() -> int:
    print(f"Starting MCP server from {SERVER_FILE.name} ...")
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER_FILE)])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = sorted(tool.name for tool in tools.tools)
            print(f"\n[1/3] tools exposed by the server: {names}")
            expected = {"list_tables", "describe_table", "run_sql"}
            if not expected.issubset(set(names)):
                print(f"      FAIL — missing tools: {sorted(expected - set(names))}")
                return 1

            ok_list = show(
                "[2/3] list_tables() ->",
                await session.call_tool("list_tables", {}),
            )
            ok_sql = show(
                '[3/3] run_sql("SELECT count(*) AS total_lots FROM lots") ->',
                await session.call_tool(
                    "run_sql", {"query": "SELECT count(*) AS total_lots FROM lots"}
                ),
            )

    if ok_list and ok_sql:
        print("\nSmoke test PASSED — Claude Desktop will be able to use this server.")
        return 0
    print("\nSmoke test FAILED — see the errors above.")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
