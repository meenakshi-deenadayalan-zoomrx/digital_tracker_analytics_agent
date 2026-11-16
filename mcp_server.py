"""DTAA MCP Server — stdio transport for the Digital Tracker Analytics Agent.

Exposes read-only SQL access to the two databases the DTAA skills query:
the Perxcept extension read replica and Synapse.

Kept deliberately thin: service modules pull in SQLAlchemy, which costs ~0.5s
to import, so they are imported inside call_tool() rather than at module level.
Nothing but `mcp` itself loads before the initialize handshake — a slow start
here shows up as "MCP server connection timed out" in the client.

The full support-agent server (GitHub, Phabricator, Playwright, filesystem)
lives in dtsa-agent, and a copy is kept alongside this file as
mcp_server_full.py.bak.

Run via:
    python mcp_server.py
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Ensure this directory is on sys.path so local imports resolve, and that .env
# is found, regardless of the working directory the client launches us from.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
os.chdir(_HERE)

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("dtaa-tools")

_QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Parameterized SQL SELECT with %(param)s placeholders"},
        "params": {"type": "object", "description": "Parameter values dict for the query placeholders", "default": {}},
        "max_rows": {"type": "integer", "description": "Max rows to return (default 100, absolute max 100)", "default": 100},
    },
    "required": ["query"],
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="dtsa_mysql_read",
            description=(
                "Execute a read-only SQL query against the Perxcept extension DB read replica. "
                "This is the Digital Tracker database holding ads, emails, posts, search and web "
                "content capture data. MUST be a SELECT statement returning aggregates "
                "(COUNT, GROUP BY). Max 100 rows returned. No raw user data."
            ),
            inputSchema=_QUERY_SCHEMA,
        ),
        Tool(
            name="synapse_mysql_read",
            description=(
                "Execute a read-only SQL query against the Synapse DB (community-data.zoomrx.com, "
                "zoomrx schema). Use for panelist attributes such as HCP specialty. "
                "MUST be a SELECT statement. Max 100 rows returned."
            ),
            inputSchema=_QUERY_SCHEMA,
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "dtsa_mysql_read":
            from mysql_service import DtsaMysqlService

            result = await DtsaMysqlService.execute_read_query(
                query=arguments["query"],
                params=arguments.get("params", {}),
                max_rows=min(arguments.get("max_rows", 100), 100),
            )
        elif name == "synapse_mysql_read":
            from synapse_mysql_service import SynapseMysqlService

            result = await SynapseMysqlService.execute_read_query(
                query=arguments["query"],
                params=arguments.get("params", {}),
                max_rows=min(arguments.get("max_rows", 100), 100),
            )
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, default=str))]
    except Exception as e:
        logger.error(f"[DTAA] Tool call failed for {name}: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
