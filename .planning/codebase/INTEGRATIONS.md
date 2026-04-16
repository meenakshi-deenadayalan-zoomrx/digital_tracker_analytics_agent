# External Integrations

**Analysis Date:** 2026-04-15

## APIs & External Services

**GitHub:**
- Commits & Diff API - Code investigation tool for ZoomRx repositories
  - SDK/Client: httpx (async HTTP client) or GitPython (local)
  - Auth: `DTSA_GITHUB_TOKEN` (PAT with repo:read scope)
  - Endpoint: `https://api.github.com`
  - Supported Repos: digitrace-chrome-extension, perxcept-ap-server, perxcept-ios, perxcept-macos, perxcept-data-processing-service
  - Implementation: `github_service.py` lines 33-252
  - Fallback: Local git repos via GitPython if token not set

**Phabricator:**
- Maniphest Task Creation (Conduit API) - Create diagnostic task tickets
  - SDK/Client: httpx (async HTTP client)
  - Auth: `DTSA_PHABRICATOR_API_TOKEN` (create-only token)
  - Endpoint: `{DTSA_PHABRICATOR_API_URL}/api/maniphest.createtask`
  - Implementation: `phabricator_service.py` lines 16-65
  - Features: Priority mapping (unbreak_now=100, high=80, normal=50, low=25), project tagging

## Data Storage

**Databases:**
- MySQL (Perxcept Extension DB read replica)
  - Connection: `DTSA_EXTENSION_DB_READ_HOST`, `DTSA_EXTENSION_DB_READ_PORT` (default 3306), `DTSA_EXTENSION_DB_READ_NAME` (extn), `DTSA_EXTENSION_DB_READ_USERNAME`, `DTSA_EXTENSION_DB_READ_PASSWORD`
  - Client: SQLAlchemy 2.0+ with mysql-connector-python driver
  - Access Pattern: Read-only queries with parameterization
  - Pool: 3 connections, 2 max overflow, 3600s recycle
  - Implementation: `dtsa_database.py` lines 11-44
  - Query Execution: `mysql_service.py` lines 17-44
  - Restrictions: SELECT only, max 100 rows per query, 30-second timeout

**File Storage:**
- Local filesystem only
  - Storage Location: Configured via `DTSA_LOCAL_REPOS_BASE` environment variable
  - Purpose: Git repository clones for code investigation
  - Allowed Extensions: .js, .ts, .jsx, .tsx, .mjs, .cjs, .py, .rb, .go, .java, .swift, .kt, .json, .yaml, .yml, .toml, .ini, .env.example, .md, .txt, .rst, .html, .css
  - Implementation: `filesystem_service.py` lines 14-24
  - Constraints: 200KB max per file, path sandboxing to repos base

**Caching:**
- None - No explicit caching layer

## Authentication & Identity

**Auth Provider:**
- GitHub PAT (Personal Access Token) - Optional
  - Implementation: `github_service.py` lines 166-171
  - Scope: repo:read (commit history access)
  - Usage: Lines 44-45, 52-53 (conditional API usage)

- Phabricator API Token - Create-only
  - Configuration: `DTSA_PHABRICATOR_API_TOKEN`
  - Usage: `phabricator_service.py` line 38
  - Included in request payload for Conduit API

- MySQL Credentials - Username/Password
  - Configuration: `DTSA_EXTENSION_DB_READ_USERNAME`, `DTSA_EXTENSION_DB_READ_PASSWORD`
  - Implementation: `dtsa_database.py` lines 13-16
  - Pattern: Connection string with quoted password

**Custom Implementation:**
- No OAuth2 or identity provider — direct credential-based authentication
- All credentials loaded from environment variables via Pydantic settings

## Monitoring & Observability

**Error Tracking:**
- None (not integrated with Sentry, Rollbar, etc.)
- Errors logged locally via Python logging module

**Logs:**
- Approach: Python logging module
  - Configuration: `logging.basicConfig(level=logging.INFO)` in `mcp_server.py` line 31
  - Handlers: stderr/stdout (default)
  - Error logging: Logger named "dtsa" with context on failures
  - Examples:
    - `github_service.py` line 112 - Git commit retrieval errors
    - `mysql_service.py` line 43 - Query execution errors
    - `playwright_service.py` line 72 - Selector validation errors
    - `phabricator_service.py` line 63 - Task creation errors

## CI/CD & Deployment

**Hosting:**
- Claude Desktop (MCP server via stdio transport)
- Configured in claude_desktop_config.json pointing to `mcp_server.py`

**CI Pipeline:**
- Not detected - No GitHub Actions, Jenkins, GitLab CI configuration

**Deployment:**
- Manual: Copy/clone repo to deployment location
- MCP registration: Point Claude Desktop config at `mcp_server.py` entry point

## Environment Configuration

**Required env vars for full functionality:**
- `DTSA_EXTENSION_DB_READ_HOST` - MySQL read replica host
- `DTSA_EXTENSION_DB_READ_USERNAME` - MySQL username
- `DTSA_EXTENSION_DB_READ_PASSWORD` - MySQL password
- One of:
  - `DTSA_GITHUB_TOKEN` - For GitHub API access, OR
  - `DTSA_LOCAL_REPOS_BASE` - For local Git repository access
- `DTSA_PHABRICATOR_API_TOKEN` - For task creation
- `DTSA_PHABRICATOR_API_URL` - For task creation

**Optional env vars:**
- `DTSA_EXTENSION_DB_READ_PORT` - MySQL port (default: 3306)
- `DTSA_EXTENSION_DB_READ_NAME` - Database name (default: extn)
- `DTSA_GITHUB_ORG` - GitHub organization (default: ZoomRx)

**Secrets location:**
- `.env` file (never committed; excluded by .gitignore)
- Example template: `.env.example` lines 1-24

## Webhooks & Callbacks

**Incoming:**
- None - MCP server is called by Claude Desktop only

**Outgoing:**
- GitHub API - Read-only (commits, diffs)
- Phabricator API - Create task (one-way POST)
- MySQL - Read-only queries (SELECT only)
- Playwright - Stateless selector validation (no state persistence)

---

*Integration audit: 2026-04-15*
