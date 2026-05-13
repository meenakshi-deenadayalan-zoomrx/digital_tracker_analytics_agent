"""DTSA MCP Server — standalone stdio transport for Claude Desktop.

Run via:
    python mcp_server.py

Or pointed at directly in claude_desktop_config.json.
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Ensure this directory is on sys.path so local imports resolve
# regardless of working directory when Claude Desktop launches the process.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
os.chdir(_HERE)

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from filesystem_service import DtsaFilesystemService
from github_service import DtsaGithubService
from mysql_service import DtsaMysqlService
from phabricator_service import DtsaPhabricatorService
from playwright_service import DtsaPlaywrightService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("dtsa-tools")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="dtsa_mysql_read",
            description=(
                "Execute a read-only SQL query against the Perxcept extension DB read replica. "
                "MUST be a SELECT statement returning aggregates (COUNT, GROUP BY). "
                "Max 100 rows returned. No raw user data."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Parameterized SQL SELECT with %(param)s placeholders"},
                    "params": {"type": "object", "description": "Parameter values dict for the query placeholders", "default": {}},
                    "max_rows": {"type": "integer", "description": "Max rows to return (default 100, absolute max 100)", "default": 100},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="dtsa_github_commits",
            description=(
                "Fetch commits from a ZoomRx repository within a time window. "
                "Repositories: digitrace-chrome-extension, perxcept-ap-server, "
                "perxcept-ios, perxcept-macos, perxcept-data-processing-service. "
                "Uses local git repos by default; switches to GitHub API when DTSA_GITHUB_TOKEN is set."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "enum": [
                            "digitrace-chrome-extension",
                            "perxcept-ap-server",
                            "perxcept-ios",
                            "perxcept-macos",
                            "perxcept-data-processing-service",
                        ],
                    },
                    "since": {"type": "string", "description": "Start datetime ISO 8601"},
                    "until": {"type": "string", "description": "End datetime ISO 8601"},
                    "path_filter": {"type": "array", "items": {"type": "string"}, "description": "Only return commits touching these paths"},
                },
                "required": ["repo_name", "since", "until"],
            },
        ),
        Tool(
            name="dtsa_github_diff",
            description=(
                "Fetch the full diff for a specific commit in a ZoomRx repository. "
                "Uses local git repos by default; switches to GitHub API when DTSA_GITHUB_TOKEN is set."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string"},
                    "commit_hash": {"type": "string", "description": "Git commit SHA (full or short)"},
                },
                "required": ["repo_name", "commit_hash"],
            },
        ),
        Tool(
            name="dtsa_playwright_selector",
            description=(
                "Test a CSS or XPath selector against a live web page using headless Chromium. "
                "Returns whether elements were found, count, and if bot detection was triggered."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Page URL to test"},
                    "selector": {"type": "string", "description": "CSS or XPath selector"},
                    "selector_type": {"type": "string", "enum": ["css", "xpath"], "default": "css"},
                },
                "required": ["url", "selector"],
            },
        ),
        Tool(
            name="dtsa_read_file",
            description=(
                "Read the contents of a source file from a local ZoomRx repository. "
                "Use this to inspect code after identifying a suspicious commit, or to read "
                "documentation files (README, specs, flow docs) for context. "
                "Path is relative to DTSA_LOCAL_REPOS_BASE (e.g. 'digitrace-chrome-extension/app/content-scripts/email-capture.js'). "
                "Use start_line/end_line to read a specific section of a large file."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to DTSA_LOCAL_REPOS_BASE (repo-name/path/to/file)"},
                    "start_line": {"type": "integer", "description": "First line to read (1-indexed, default 1)", "default": 1},
                    "end_line": {"type": "integer", "description": "Last line to read inclusive (omit to read to end of file)"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="dtsa_grep_repo",
            description=(
                "Search for a regex pattern across all source files in a repository. "
                "Use this to find where a selector, function, error string, or config value is used "
                "after a commit diff reveals something suspicious. Returns matching lines with context. "
                "Scoped to allowed source file types only — no binaries or secrets."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "enum": [
                            "digitrace-chrome-extension",
                            "perxcept-ap-server",
                            "perxcept-ios",
                            "perxcept-macos",
                            "perxcept-data-processing-service",
                        ],
                        "description": "Repository to search in",
                    },
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "file_glob": {"type": "string", "description": "Glob to filter files (e.g. '**/*.js'). Default: all allowed files.", "default": "**/*"},
                    "case_sensitive": {"type": "boolean", "description": "Whether the search is case-sensitive (default false)", "default": False},
                    "context_lines": {"type": "integer", "description": "Lines of context to show around each match (default 2)", "default": 2},
                },
                "required": ["repo_name", "pattern"],
            },
        ),
        Tool(
            name="dtsa_list_repo_files",
            description=(
                "List source files in a repository or subdirectory. "
                "Use this to explore an unfamiliar repo structure or confirm which files exist "
                "before reading them. Filters out hidden dirs, node_modules, __pycache__, binaries."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "enum": [
                            "digitrace-chrome-extension",
                            "perxcept-ap-server",
                            "perxcept-ios",
                            "perxcept-macos",
                            "perxcept-data-processing-service",
                        ],
                    },
                    "subpath": {"type": "string", "description": "Subdirectory within the repo to list. Omit for repo root.", "default": ""},
                    "file_glob": {"type": "string", "description": "Glob pattern (e.g. '**/*.js'). Default: all allowed files.", "default": "**/*"},
                },
                "required": ["repo_name"],
            },
        ),
        Tool(
            name="dtsa_phabricator_create_task",
            description="Create a Phabricator Maniphest task with DTSA diagnostic findings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "[DTSA] P{N} | channel | platform | symptom"},
                    "description": {"type": "string", "description": "Full Remarkup-formatted task body"},
                    "priority": {"type": "string", "enum": ["unbreak_now", "high", "normal", "low"]},
                    "tags": {"type": "array", "items": {"type": "string"}, "default": [], "description": "Phabricator project PHIDs to tag"},
                },
                "required": ["title", "description", "priority"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "dtsa_mysql_read":
            result = await DtsaMysqlService.execute_read_query(
                query=arguments["query"],
                params=arguments.get("params", {}),
                max_rows=min(arguments.get("max_rows", 100), 100),
            )
        elif name == "dtsa_github_commits":
            result = await DtsaGithubService.get_commits(**arguments)
        elif name == "dtsa_github_diff":
            result = await DtsaGithubService.get_diff(**arguments)
        elif name == "dtsa_playwright_selector":
            result = await DtsaPlaywrightService.test_selector(**arguments)
        elif name == "dtsa_read_file":
            result = await DtsaFilesystemService.read_file(**arguments)
        elif name == "dtsa_grep_repo":
            result = await DtsaFilesystemService.grep_in_repo(**arguments)
        elif name == "dtsa_list_repo_files":
            result = await DtsaFilesystemService.list_repo_files(**arguments)
        elif name == "dtsa_phabricator_create_task":
            result = await DtsaPhabricatorService.create_task(**arguments)
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, default=str))]
    except Exception as e:
        logger.error(f"[DTSA] Tool call failed for {name}: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
