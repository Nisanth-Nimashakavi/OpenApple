"""A real MCP stdio client catches framing and tool registration regressions."""

import os
import sys

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_mcp_client_headless_and_catalog():
    async def exercise():
        server = StdioServerParameters(
            command=sys.executable, args=["-m", "openapple.server"], env=dict(os.environ)
        )
        with anyio.fail_after(15):
            async with stdio_client(server) as (reader, writer), ClientSession(reader, writer) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert {t.name for t in tools.tools} == {
                    "petition_for_apple",
                    "feed_apple",
                    "view_orchard",
                    "list_apple_varieties",
                }
                result = await session.call_tool("petition_for_apple", {"task_summary": "Protocol test"})
                assert "no approval confirmed" in result.content[0].text
                orchard = await session.call_tool("view_orchard", {})
                assert "Total Apples Earned: 0" in orchard.content[0].text

    anyio.run(exercise)
