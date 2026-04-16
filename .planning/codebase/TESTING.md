# Testing Patterns

**Analysis Date:** 2026-04-15

## Test Framework

**Status:** Not detected

**Analysis:**
- No test files found (no `*_test.py`, `test_*.py`, or `*_spec.py` in project root or service directories)
- No test runner configured: `pytest.ini`, `setup.cfg`, `conftest.py` not found
- No assertion/mocking libraries in `requirements.txt`: no pytest, unittest, mock, or hypothesis
- `pyproject.toml` contains no test tool configuration

**Required Testing Infrastructure:**
To add tests, install:
```bash
pip install pytest pytest-asyncio httpx-mock pytest-playwright
```

## Testing Approach (Current State)

**Manual Testing Only:**
The SETUP.md documents a manual verification step:
```bash
# macOS / Linux
/path/to/dtsa-mcp-server/.venv/bin/python /path/to/dtsa-mcp-server/mcp_server.py

# Windows
C:\path\to\dtsa-mcp-server\.venv\Scripts\python.exe C:\path\to\dtsa-mcp-server\mcp_server.py
```

Verification in Claude Desktop:
1. Start new conversation
2. Type: `What diagnostic tools do you have available?`
3. Verify 8 tools listed
4. Type `/dtsa` — orchestrator skill should activate

## Architecture Supporting Testing

**Service Isolation:**
The codebase is structured to support unit testing despite no tests being present:

**Services are static method containers:**
```python
class DtsaFilesystemService:
    @staticmethod
    async def read_file(path: str, start_line: int = 1, end_line: int | None = None) -> dict:
        # no instance state
```

**No constructors or initialization:** Services can be called directly without setup

**Dependency injection via imports:**
- `from config import env` — Settings singleton injected at module level
- Can be mocked by replacing `env` values in tests

**Return dicts, not custom types:**
- All methods return `dict` — compatible with JSON serialization and easy assertions
- Makes fixtures simple: just compare dict keys and values

## How to Test Each Service

### Testing Pattern (not currently used):

**1. Filesystem Service (`filesystem_service.py`)**

*What to test:*
- Path escaping vulnerability: confirm `_resolve_safe()` rejects paths outside base
- File size limit: confirm `read_file()` returns error for files > 200KB
- File type filtering: confirm non-source files (.bin, .exe) rejected
- Line range parsing: confirm `start_line`/`end_line` work correctly

*Mocking needed:*
```python
# Mock filesystem
from pathlib import Path
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_path_escaping():
    """Confirm path/../etc/passwd is rejected."""
    # Monkeypatch env.DTSA_LOCAL_REPOS_BASE
    result = await DtsaFilesystemService.read_file("../../../etc/passwd")
    assert result["error"]
    assert "outside" in result["error"]
```

**2. GitHub Service (`github_service.py`)**

*What to test:*
- Local git path resolution
- Commit parsing from gitpython
- Diff formatting and truncation at 5000 bytes
- ISO timestamp parsing (`_parse_iso()`)
- GitHub API fallback when `DTSA_GITHUB_TOKEN` set

*Mocking needed:*
```python
# Mock git.Repo or httpx.AsyncClient

@pytest.mark.asyncio
async def test_github_api_commits(monkeypatch):
    """Verify GitHub API used when token set."""
    monkeypatch.setenv("DTSA_GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("DTSA_GITHUB_ORG", "TestOrg")
    
    # Mock httpx.AsyncClient.get()
    result = await DtsaGithubService.get_commits(
        repo_name="test-repo",
        since="2026-01-01T00:00:00Z",
        until="2026-01-31T23:59:59Z",
    )
    assert result["source"] == "github_api"
```

**3. Playwright Service (`playwright_service.py`)**

*What to test:*
- Bot detection signature matching (Cloudflare, reCAPTCHA, etc.)
- Selector validation (CSS vs XPath)
- Element counting
- Navigation timeout handling
- Browser cleanup on error

*Mocking needed:*
```python
# Mock playwright.async_playwright

@pytest.mark.asyncio
async def test_bot_detection():
    """Confirm bot detection returns 'blocked: True'."""
    # Mock page.content() to return Cloudflare signature
    result = await DtsaPlaywrightService.test_selector(
        url="https://example.com",
        selector=".blocked",
        selector_type="css",
    )
    assert result["blocked"] is True
    assert result["found"] is False
```

**4. MySQL Service (`mysql_service.py`)**

*What to test:*
- SQL injection prevention: confirm INSERT/UPDATE/DELETE rejected
- LIMIT auto-append when missing
- Row limit enforcement (max 100)
- Parameter substitution (%(param)s placeholders)
- Timeout enforcement (30000ms)

*Mocking needed:*
```python
# Mock SQLAlchemy session

@pytest.mark.asyncio
async def test_forbidden_operations():
    """Confirm INSERT/UPDATE/DELETE rejected."""
    result = await DtsaMysqlService.execute_read_query(
        query="DELETE FROM users WHERE id = 1",
        params={},
    )
    assert result["error"]
    assert "Only SELECT" in result["error"]
```

**5. Phabricator Service (`phabricator_service.py`)**

*What to test:*
- API token validation
- Priority mapping (unbreak_now → 100, high → 80, etc.)
- Task ID extraction from response
- Error handling from Conduit API

*Mocking needed:*
```python
# Mock httpx.AsyncClient.post()

@pytest.mark.asyncio
async def test_task_creation(monkeypatch):
    """Verify task creation formats request correctly."""
    monkeypatch.setenv("DTSA_PHABRICATOR_API_TOKEN", "test-token")
    monkeypatch.setenv("DTSA_PHABRICATOR_API_URL", "https://phab.test.com")
    
    # Mock httpx response
    result = await DtsaPhabricatorService.create_task(
        title="[DTSA] P1 | Email | iOS | Low CTR",
        description="Test task",
        priority="high",
    )
    assert result["success"] is True
    assert result["task_id"].startswith("T")
```

**6. MCP Server (`mcp_server.py`)**

*What to test:*
- Tool listing (`@server.list_tools()`)
- Tool dispatch (`@server.call_tool()`)
- Error handling and JSON serialization
- Parameter validation via schemas

*Mocking needed:*
```python
# Mock MCP server and tool implementations

@pytest.mark.asyncio
async def test_tool_list():
    """Verify all 8 tools are registered."""
    tools = await list_tools()
    assert len(tools) == 8
    names = {t.name for t in tools}
    assert "dtsa_mysql_read" in names
    assert "dtsa_github_commits" in names
```

## Integration Testing Approach

**Currently:** Manual in Claude Desktop (see SETUP.md Step 7)

**Recommended approach when tests added:**
```bash
# Start MCP server
python mcp_server.py &
SERVER_PID=$!

# Run integration tests against stdio transport
pytest tests/integration/

# Cleanup
kill $SERVER_PID
```

## Test Data / Fixtures

**Recommended fixture structure (not currently in place):**
```
tests/
├── fixtures/
│   ├── sample_repos/              # minimal git repos for testing
│   ├── sample_files/              # small test files
│   └── sample_queries.py           # SQL queries for testing
├── unit/
│   ├── test_filesystem_service.py
│   ├── test_github_service.py
│   └── test_mysql_service.py
└── integration/
    └── test_mcp_server.py
```

## Coverage

**Requirements:** None enforced

**Current State:** Zero. No test files to measure.

**Recommendation:** Establish baseline target of 80% statement coverage for service methods (core I/O paths).

## Test Types

**Unit Tests (should be added):**
- Test each service method in isolation
- Mock external dependencies (filesystem, git, httpx, playwright, sqlalchemy)
- Scope: single function, verify input validation, error handling, output format

**Integration Tests (should be added):**
- Test MCP server dispatch: call tool, verify response structure
- Test end-to-end flows: real or stubbed databases, APIs
- Scope: multiple services interacting

**E2E Tests (not applicable):**
- The system is an MCP server. E2E would mean testing via Claude Desktop or MCP client.
- Manual testing via Claude Desktop (SETUP.md Step 7) is the current E2E approach.

## Async Testing Pattern (when added)

**Use `pytest-asyncio`:**
```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    result = await DtsaFilesystemService.read_file("test.txt")
    assert result["path"] == "test.txt"
```

**Fixture for async setup:**
```python
@pytest.fixture
async def configured_env(monkeypatch):
    monkeypatch.setenv("DTSA_LOCAL_REPOS_BASE", "/tmp/test-repos")
    yield
```

## Error Testing Pattern (when added)

**Test error paths explicitly:**
```python
@pytest.mark.asyncio
async def test_file_not_found():
    result = await DtsaFilesystemService.read_file("nonexistent.txt")
    assert "error" in result
    assert "not found" in result["error"].lower()

@pytest.mark.asyncio
async def test_invalid_regex():
    result = await DtsaFilesystemService.grep_in_repo(
        repo_name="test-repo",
        pattern="[invalid(regex",
    )
    assert "error" in result
    assert "Invalid regex" in result["error"]
```

## Security Testing (when added)

**Path traversal prevention:**
```python
@pytest.mark.asyncio
async def test_path_traversal_blocked():
    """Confirm ../../../etc/passwd is rejected."""
    result = await DtsaFilesystemService.read_file("../../../etc/passwd")
    assert "error" in result

@pytest.mark.asyncio
async def test_symlink_escapes_blocked():
    """Confirm symlinks outside base are not followed."""
    # Create symlink pointing outside base
    result = await DtsaFilesystemService.read_file("symlink-to-outside")
    assert "error" in result
```

**SQL injection prevention:**
```python
@pytest.mark.asyncio
async def test_sql_injection_blocked():
    """Confirm payloads like ' OR '1'='1 are rejected."""
    result = await DtsaMysqlService.execute_read_query(
        query="SELECT * FROM users WHERE id = %(id)s OR 1=1",
        params={"id": 1},
    )
    # Should execute safely (parameterized), OR check is SQL-level
    # Verify no error from parameter injection
```

---

*Testing analysis: 2026-04-15*
