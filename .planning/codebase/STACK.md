# Technology Stack

**Analysis Date:** 2026-04-15

## Languages

**Primary:**
- Python 3.10+ - Core MCP server implementation, all service modules, CLI tools

## Runtime

**Environment:**
- Python 3.10 or higher (specified in `pyproject.toml`)

**Package Manager:**
- pip (via pyproject.toml and requirements.txt)
- Lockfile: `requirements.txt` pinned

## Frameworks

**Core:**
- mcp >=1.0.0 - Model Context Protocol server framework (`mcp_server.py`)
  - Transport: stdio (integrated with Claude Desktop)
  - Server initialization in `mcp_server.py` lines 34-242

**HTTP/Web:**
- httpx >=0.27.0 - Async HTTP client for GitHub API and Phabricator API calls
  - Used in `github_service.py` lines 174-251
  - Used in `phabricator_service.py` lines 33-64

**Browser Automation:**
- Playwright >=1.40.0 - Headless Chromium for selector validation and bot detection
  - Implementation: `playwright_service.py` lines 1-74
  - Features: viewport configuration, user-agent spoofing, network idle detection

**Database ORM:**
- SQLAlchemy >=2.0.0 - SQL query execution and connection pooling
  - Implementation: `dtsa_database.py` lines 1-45
  - Used in `mysql_service.py` lines 19-44

**Database Driver:**
- mysql-connector-python >=9.0.0 - MySQL protocol driver
  - Connection string format: `mysql+mysqlconnector://`
  - Pool configuration: 3 size, 2 max overflow, 3600s recycle

**Validation:**
- Pydantic >=2.0.0 - Configuration schema validation
- Pydantic-settings >=2.0.0 - Environment variable parsing
  - Settings class: `config.py` lines 1-29
  - Configuration pattern: `.env` file with defaults

**Version Control:**
- GitPython >=3.1.0 - Local Git repository operations
  - Local commits API: `github_service.py` lines 68-114
  - Local diff generation: `github_service.py` lines 117-159

## Key Dependencies

**Critical:**
- mcp - Protocol layer between MCP server and Claude Desktop
  - MCP version 1.0+ required for server/tool registration
- SQLAlchemy >=2.0.0 - Enforced for query parameterization and execution safety
- Pydantic >=2.0.0 - Settings validation prevents misconfiguration

**Infrastructure:**
- mysql-connector-python - MySQL read replica connection (Perxcept extension DB)
- httpx - All external API calls (GitHub, Phabricator)
- Playwright - Browser-based selector validation and bot detection
- GitPython - Local Git repository access for code investigation

## Configuration

**Environment:**
- Configuration via `.env` file (see `.env.example`)
- Loaded by Pydantic BaseSettings in `config.py`
- Pattern: environment variables with DTSA_ prefix

**Build:**
- `pyproject.toml` - Project metadata, Python version constraint, dependencies
- `requirements.txt` - Pinned dependency versions for reproducible installs

**Key Environment Variables:**
- `DTSA_EXTENSION_DB_READ_HOST`, `DTSA_EXTENSION_DB_READ_PORT`, `DTSA_EXTENSION_DB_READ_NAME`, `DTSA_EXTENSION_DB_READ_USERNAME`, `DTSA_EXTENSION_DB_READ_PASSWORD` - MySQL read replica credentials
- `DTSA_GITHUB_TOKEN` - GitHub PAT (optional; local repos used if empty)
- `DTSA_GITHUB_ORG` - GitHub organization (default: "ZoomRx")
- `DTSA_LOCAL_REPOS_BASE` - Base path for local repository clones
- `DTSA_PHABRICATOR_API_TOKEN` - Phabricator create-only token
- `DTSA_PHABRICATOR_API_URL` - Phabricator Conduit API endpoint

## Platform Requirements

**Development:**
- Python 3.10+
- pip package manager
- Local filesystem access (for local Git repos)
- Optional: GitHub PAT for API-based commits (instead of local repos)

**Production:**
- Python 3.10+ runtime
- Network access to:
  - MySQL read replica (Perxcept extension DB)
  - GitHub API (optional, if using GitHub token)
  - Phabricator Conduit API
- Local filesystem for storing Git repository clones (if not using GitHub API)
- Headless Chromium browser (provided by Playwright; auto-downloaded on first run)

---

*Stack analysis: 2026-04-15*
