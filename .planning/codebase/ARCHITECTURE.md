# Architecture

**Analysis Date:** 2026-04-15

## Pattern Overview

**Overall:** MCP Server (Model Context Protocol) — Standalone stdio transport exposing 8 Claude tools to Digital Tracker agents (DTSA + DTAA). Single-server pattern with layered service architecture.

**Key Characteristics:**
- Stdio-based MCP server (async) — Claude Desktop launches `mcp_server.py` directly
- Service-oriented architecture — Each integration (MySQL, GitHub, Playwright, Phabricator, Filesystem) has dedicated service class
- Configuration-driven — Environment variables control behavior (GitHub API vs local git, database credentials)
- Stateless tool handlers — Each tool call is independent, no shared session state
- Security-focused — Read-only database, sandboxed filesystem, regex validation, bot detection

## Layers

**MCP Server Layer:**
- Purpose: Expose tools to Claude via stdio, route tool calls to service implementations
- Location: `mcp_server.py`
- Contains: Tool definitions, MCP server initialization, tool call dispatcher
- Depends on: All service classes (MySQL, GitHub, Playwright, Phabricator, Filesystem)
- Used by: Claude Desktop (external)

**Service Layer:**
- Purpose: Implement tool logic with safety guardrails, error handling, SDK/API integration
- Location: `mysql_service.py`, `github_service.py`, `playwright_service.py`, `phabricator_service.py`, `filesystem_service.py`
- Contains: Static async methods for tool operations
- Depends on: Configuration, external libraries (SQLAlchemy, gitpython, httpx, playwright)
- Used by: MCP server dispatcher

**Configuration Layer:**
- Purpose: Load environment variables with Pydantic validation
- Location: `config.py`
- Contains: Settings class mapping env vars → Python attributes
- Depends on: `.env` file (or absent)
- Used by: Service classes

**Database Layer:**
- Purpose: Manage SQLAlchemy connection pooling to Perxcept extension DB read replica
- Location: `dtsa_database.py`
- Contains: Session factory, context manager for lifecycle
- Depends on: Configuration, SQLAlchemy
- Used by: MySQL service

**Skills Layer (Claude agent instructions):**
- Purpose: Provide agent behavior and routing rules
- Location: `skills/` — organized by agent system (DTSA, DTAA) and channels
- Contains: SKILL.md orchestrators and reference documentation
- Depends on: MCP tools (calls from agents)
- Used by: DTSA + DTAA agents

## Data Flow

**Tool Call Flow:**

1. Claude agent invokes MCP tool (e.g., `dtsa_mysql_read` with `query` parameter)
2. `mcp_server.py` → `call_tool()` receives tool name + arguments
3. Dispatcher routes to appropriate service method (e.g., `DtsaMysqlService.execute_read_query()`)
4. Service validates input (SQL regex check, path sandbox, selector type enum)
5. Service executes operation (DB query, git command, playwright launch, API call, file read)
6. Service returns structured result dict
7. MCP server wraps result in `TextContent` and returns to Claude
8. Claude receives JSON response, parses and acts on result

**State Management:**
- None per-request — each tool call is independent
- SQLAlchemy session factory maintains connection pool (singleton pattern in `dtsa_database.py`)
- GitHub service auto-selects GitHub API vs local git based on env var presence
- No user session tracking, no conversation context

## Key Abstractions

**Tool Definition:**
- Purpose: Declarative schema for MCP tool
- Examples: `dtsa_mysql_read` (lines 41–56 in `mcp_server.py`), `dtsa_playwright_selector` (lines 100–115)
- Pattern: `Tool(name=..., description=..., inputSchema={type, properties, required})`

**Service Class:**
- Purpose: Encapsulate integration logic with static async methods
- Examples: `DtsaMysqlService`, `DtsaGithubService`, `DtsaPlaywrightService`
- Pattern: Static class with `@staticmethod async def tool_handler(...) -> dict`

**Safety Sandboxing:**
- Filesystem: Path resolution + containment check (`_resolve_safe()` in `filesystem_service.py` lines 38–49)
- Database: SQL pattern matching (forbidden keywords regex line 11–14 in `mysql_service.py`)
- GitHub: Repo allowlist (line 14–20 in `github_service.py`)
- Playwright: Bot detection signature matching (BOT_SIGS list line 10–18 in `playwright_service.py`)

**Dual Source Pattern (GitHub Service):**
- Purpose: Support local git repos during development, GitHub API in production
- Examples: `_local_get_commits()` vs `_github_get_commits()` (lines 68–211 in `github_service.py`)
- Pattern: `_use_github_api()` conditional routing

## Entry Points

**`mcp_server.py` main():**
- Location: `mcp_server.py` lines 240–246
- Triggers: `python mcp_server.py` or Claude Desktop config points here
- Responsibilities: Initialize MCP server, launch stdio event loop, register tool handler

**Tool Handlers:**
- Location: `mcp_server.py` lines 37–205 (tool list) + 208–237 (call dispatcher)
- Triggers: Claude agent invokes tool by name
- Responsibilities: Validate tool exists, call service method, format response

## Error Handling

**Strategy:** Fail gracefully — return `{"error": "reason"}` dict instead of raising exceptions. Exceptions are caught at service level, logged, and wrapped in response.

**Patterns:**

1. **Input Validation Error** — Return early with message before operation
   - Example: `mysql_service.py` lines 20–23 (forbidden SQL keywords)
   - Example: `filesystem_service.py` lines 54–61 (path validation)

2. **Operation Failure** — Catch exception, log, return error dict
   - Example: `mysql_service.py` lines 42–44 (db execute exception)
   - Example: `github_service.py` lines 112–114, 158–159 (git/API exception)

3. **Logging** — `logger.error()` prefixed with `[DTSA]` for grep-ability
   - All services use `logger.error()` to record failures

4. **Bot Detection** — Return `blocked: True` flag instead of error
   - `playwright_service.py` lines 47–56 (Cloudflare, reCAPTCHA signatures)

## Cross-Cutting Concerns

**Logging:** All services use Python `logging` module. Entry point sets `logging.basicConfig(level=logging.INFO)` (line 31 in `mcp_server.py`). All errors logged with `[DTSA]` prefix for clarity.

**Validation:** Multi-layer approach:
- Tool schema validation (MCP framework validates inputSchema match)
- Input validation in service (SQL regex, path resolve, enum check)
- External validation (bot detection, API response status)

**Authentication:**
- MySQL: Credentials from env vars (username/password in connection URL, line 13 in `dtsa_database.py`)
- GitHub: Optional PAT token from env var (switches to GitHub API, line 18 in `github_service.py`)
- Phabricator: Conduit API token from env var (line 25 in `phabricator_service.py`)
- Filesystem: No auth, but sandboxed to `DTSA_LOCAL_REPOS_BASE`

---

*Architecture analysis: 2026-04-15*
