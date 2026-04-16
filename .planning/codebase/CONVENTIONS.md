# Coding Conventions

**Analysis Date:** 2026-04-15

## Naming Patterns

**Files:**
- Service classes: `{service_name}_service.py` (e.g., `filesystem_service.py`, `github_service.py`)
- Database/config: `{component}_database.py`, `config.py`
- Entry point: `mcp_server.py`
- All lowercase with underscores (snake_case)

**Functions/Methods:**
- `snake_case` for all functions and methods
- Static methods preferred for utility/service classes: `@staticmethod`
- Async methods use `async def` and prefix parameter calls with `await`
- Helper methods prefixed with single underscore: `_parse_iso()`, `_resolve_safe()`, `_use_github_api()`
- Public methods: no prefix

**Classes:**
- `PascalCase` for all class names
- Service classes: `Dtsa{ServiceName}Service` (e.g., `DtsaFilesystemService`, `DtsaMysqlService`)
- All implemented as static method containers — no instance state

**Variables/Constants:**
- Global constants: `UPPERCASE_WITH_UNDERSCORES` (e.g., `ALLOWED_EXTENSIONS`, `MAX_FILE_BYTES`, `FORBIDDEN`)
- Local variables: `snake_case`
- Environment variables: `DTSA_` prefix (e.g., `DTSA_LOCAL_REPOS_BASE`, `DTSA_EXTENSION_DB_READ_HOST`)
- Pydantic Settings class: `Settings` (capital S)

**Types:**
- Type hints used throughout: `-> dict`, `-> str | None`, `list[str]`
- Union types use pipe `|` (Python 3.10+): `str | None` not `Optional[str]`
- Generic types: `list[str]`, `dict[str, int]`

## Code Style

**Formatting:**
- No explicit formatter configured (`.prettierrc`, `black` config, or `.editorconfig` not found)
- Consistent 4-space indentation observed throughout
- Double quotes for strings: `"error"`, `"url"`, `"pattern"`
- Line wrapping: functions/methods respect ~100 character logical breaks

**Linting:**
- No `.flake8`, `pylint`, or `pyproject.toml` linting config found
- Style enforced by code review and consistency, not automated tools

**Import Organization:**
- Standard library first: `import asyncio`, `import json`, `import logging`, `import os`, `import sys`, `from pathlib import Path`, `from datetime import datetime`
- Third-party: `from pydantic_settings import BaseSettings`, `from sqlalchemy import ...`, `from mcp.server import Server`
- Local imports last: `from config import env`, `from filesystem_service import DtsaFilesystemService`
- Blank lines between groups

**Order example from `mcp_server.py`:**
```python
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from filesystem_service import DtsaFilesystemService
from github_service import DtsaGithubService
```

## Module Design

**Exports:**
- No `__all__` declarations — all public symbols are exported implicitly
- Service classes are the primary export (e.g., `DtsaFilesystemService` from `filesystem_service.py`)
- Constants and helpers at module level or as static class members

**Barrel Files:**
- Not used. Each service has its own module.

**Pydantic Configuration:**
- `Settings` class uses `BaseSettings` with `SettingsConfigDict`
- Config pattern: `model_config = SettingsConfigDict(env_file=".env", extra="ignore")`
- Load via: `env = Settings()` singleton at module level

## Error Handling

**Patterns:**
- Try/except wraps all I/O operations: database, filesystem, HTTP, git operations
- Return `dict` with `"error"` key on failure — never raise exceptions to caller
- Error messages are informative: `{"error": f"Path '{path}' is outside the allowed repos base or invalid"}`
- Log exceptions via `logger.error()` before returning error dict
- Resource cleanup via context managers: `@contextmanager`, `async with`, `try/finally`

**Error Response Pattern:**
```python
try:
    # operation
except Exception as e:
    logger.error(f"[DTSA] Operation failed: {e}")
    return {"error": str(e), "query": query}
```

**Async Exception Pattern:**
```python
try:
    result = await async_operation()
except Exception as e:
    await browser.close()  # cleanup
    return {"url": url, "error": f"Navigation failed: {e}", "found": False}
```

## Logging

**Framework:** Standard library `logging`

**Setup:**
```python
logger = logging.getLogger(__name__)
```

**Patterns:**
- Log level: `logger.error()` for exceptions and failures
- Format: `f"[DTSA] {operation} failed: {e}"` — all errors prefixed with `[DTSA]`
- Used only in exception handlers — not for normal flow tracking
- Logging configured at entry point: `logging.basicConfig(level=logging.INFO)` in `mcp_server.py`

**Example from `github_service.py`:**
```python
logger.error(f"[DTSA] Local git commits failed for {repo_name}: {e}")
logger.error(f"[DTSA] GitHub API diff failed: {e}")
```

## Comments

**When to Comment:**
- Module docstrings: one-liner describing purpose and scope
- Docstrings on methods: explain tricky logic (e.g., security boundary check)
- Section dividers for major logical blocks (e.g., `# ------------------------------------------------------------------ #`)
- No inline comments for obvious code

**JSDoc/TSDoc:**
- Not used (Python codebase)
- Method docstrings are minimal and focused on behavior/security

**Example from `filesystem_service.py`:**
```python
@staticmethod
def _resolve_safe(path: str) -> Path | None:
    """Resolve path and confirm it sits under DTSA_LOCAL_REPOS_BASE."""
```

## Function Design

**Size:**
- Prefer functions under 50 lines
- Longer functions (50-100 lines) are acceptable for service operations with complex try/except
- No explicit line count enforcement

**Parameters:**
- Type hints required on all parameters and returns
- Default values provided for optional params: `context_lines: int = 2`, `start_line: int = 1`
- Avoid positional-only or keyword-only unless essential

**Return Values:**
- Consistent return type: always `dict` for public methods
- Response dict includes: success indicators (`"found"`, `"success"`), data fields, error messages
- Never return `None` — return error dict instead: `{"error": "..."}`

**Example:**
```python
async def read_file(path: str, start_line: int = 1, end_line: int | None = None) -> dict:
    # ... validation ...
    return {
        "path": path,
        "total_lines": total_lines,
        "showing_lines": f"{start + 1}–{end}",
        "content": numbered,
        "truncated": end < total_lines,
    }
```

## Async/Await

**Pattern:**
- Top-level methods async: `async def list_commits(...) -> dict:`
- Called with `await`: `result = await DtsaGithubService.get_commits(...)`
- Used for I/O: network (httpx), file I/O, browser automation (playwright)
- Exceptions properly awaited during cleanup: `await browser.close()`

## Constants and Globals

**Pattern:**
- Module-level constants: `ALLOWED_REPOS`, `MAX_FILE_BYTES`, `FORBIDDEN`
- Lazy-initialized globals for shared state: `_engine`, `_SessionFactory` in `dtsa_database.py`
- Initialization check: `if _SessionFactory is None:`

**Example from `dtsa_database.py`:**
```python
_engine = None
_SessionFactory = None

def _get_session_factory():
    global _engine, _SessionFactory
    if _SessionFactory is None:
        _engine = create_engine(...)
        _SessionFactory = sessionmaker(...)
    return _SessionFactory
```

## Security Boundaries

**Input Validation:**
- Path escaping check: `resolved.relative_to(base)` ensures path stays within sandbox
- Regex validation: `re.compile(pattern, flags)` with error catching
- SQL injection prevention: parameterized queries with `%(param)s` placeholders
- Forbidden SQL operations: regex check `FORBIDDEN.search(query)` for INSERT/UPDATE/DELETE

**Example from `mysql_service.py`:**
```python
FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|REPLACE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

if FORBIDDEN.search(query):
    return {"error": "Only SELECT queries are allowed", "query": query}
```

---

*Convention analysis: 2026-04-15*
