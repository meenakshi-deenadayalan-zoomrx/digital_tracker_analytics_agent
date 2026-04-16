# Codebase Concerns

**Analysis Date:** 2026-04-15

## Tech Debt

**Overly Broad Exception Handling:**
- Issue: Multiple service classes catch `Exception` without distinguishing error types, making debugging harder and hiding unexpected failures
- Files: `mysql_service.py:42`, `github_service.py:112,157,211,249`, `filesystem_service.py:43,75,135`, `playwright_service.py:39,71`, `phabricator_service.py:62`, `mcp_server.py:235`
- Impact: Legitimate errors (network failures, missing repos, invalid credentials) are indistinguishable from code bugs. Agent cannot determine if a tool failure is expected vs. unexpected.
- Fix approach: Use granular exception types — separate `FileNotFoundError`, `PermissionError`, `TimeoutError`, `ValidationError`. Log specific error categories. Return structured error responses distinguishing transient failures from permanent misconfigurations.

**Delayed Import Pattern Creates Fragility:**
- Issue: `git` and `httpx` modules are imported inside methods only when needed, not at module level
- Files: `github_service.py:75,119,181,218`, `phabricator_service.py:34`
- Impact: Missing dependencies not caught until tool is called at runtime. Fails silently in try-except blocks. Increases latency on first call to any github/phabricator operation.
- Fix approach: Import all required modules at module level in `__init__` or during server startup. Fail fast with clear error during MCP server initialization.

**Unclosed Database Sessions on Query Errors:**
- Issue: `mysql_service.py` acquires a session via `get_extension_read_db()` context manager, but if `session.execute()` throws an exception, session cleanup still occurs (context manager ensures this). However, no timeout is set on the session itself, only on query execution.
- Files: `mysql_service.py:28-44`, `dtsa_database.py:37-44`
- Impact: Long-running queries that exceed MAX_EXECUTION_TIME=30000 may leave connections stuck. Pool exhaustion possible under load.
- Fix approach: Set connection-level timeout and statement timeout at session creation time. Add explicit connection close on error. Monitor pool usage.

## Known Bugs

**Playwright Browser Not Always Closed on Error:**
- Issue: If `page.goto()` fails, browser is closed. But if any of the subsequent operations fail (locator lookup, content read), browser is closed in try-except but not in a finally block
- Files: `playwright_service.py:25-73`
- Impact: If `await page.locator(loc).all()` or `await page.content()` throws an unexpected exception, the outer try-except at line 71 catches it, but that exception path doesn't execute the `await browser.close()` at line 61. Browser process remains alive and consumes resources.
- Workaround: None currently. Each failed selector test leaks a Chromium process.
- Fix approach: Use try-finally or ensure `browser.close()` is called in all exception paths. Refactor to use context manager or defer cleanup.

**Path Resolution Does Not Handle Symlinks Safely:**
- Issue: `filesystem_service.py` uses `Path.resolve()` which follows symlinks, then checks if path is within `DTSA_LOCAL_REPOS_BASE`. Symlink in repos pointing outside base directory bypasses sandbox.
- Files: `filesystem_service.py:42-49`, `filesystem_service.py:178-182`
- Impact: Agent could theoretically read files outside the configured repos base via symlink traversal if repos contain symlinks.
- Workaround: Ensure repos do not contain symlinks pointing outside base directory.
- Fix approach: Check if resolved path's parent chain contains symlinks. Use `Path.is_symlink()` and `Path.readlink()` to validate symlink targets stay within base.

**Regex Pattern in grep_in_repo Not Validated for ReDoS:**
- Issue: `filesystem_service.py:114` compiles user-provided regex patterns without limits or validation
- Files: `filesystem_service.py:112-116`
- Impact: User could provide catastrophic regex like `(a+)+b` causing exponential backtracking and hanging the tool on any matching file.
- Workaround: Use simple patterns only (no nested quantifiers).
- Fix approach: Timeout the regex compilation and matching. Use safer regex engine or validate pattern structure upfront.

## Security Considerations

**Database Credentials Exposed in Connection String:**
- Risk: `dtsa_database.py:13-16` constructs a MySQL connection URL containing password, which may appear in logs or error messages
- Files: `dtsa_database.py:13-16`
- Current mitigation: Stored in environment variable, only built once at engine creation
- Recommendations: Never log the connection URL. Mask password in any error messages. Use connection pooling to minimize credential exposure window.

**SQL Injection via Dynamic Query String Manipulation:**
- Risk: Although `mysql_service.py` validates queries with regex and requires SELECT, the dynamic LIMIT injection at line 31 concatenates the limit value into the query string rather than parameterizing it
- Files: `mysql_service.py:30-31`
- Current mitigation: `max_rows` is validated as integer and capped at 100, then int-formatted into string
- Recommendations: Ensure all query construction happens via parameterized queries, even for LIMIT clauses. Use SQLAlchemy's compiled query binding.

**GitHub API Token Appears in Authorization Header:**
- Risk: Token is sent in clear text in HTTP Authorization header. If logs capture request/response, token is exposed.
- Files: `github_service.py:166-170`
- Current mitigation: HTTPS used, token is create-only (limited scope)
- Recommendations: Never log headers. Mask token in error messages. Rotate token regularly. Use short-lived tokens if GitHub allows.

**File Read Has 200KB Limit But No Virus/Malware Scanning:**
- Risk: Agent can read arbitrary files up to 200KB from disk. While filesystem sandbox is in place, the content itself may contain malicious payloads (binary files, embedded exploits).
- Files: `filesystem_service.py:26,52-91`
- Current mitigation: File type whitelist (ALLOWED_EXTENSIONS), limits to source/config/doc files
- Recommendations: Be explicit about acceptable file types. Reject binary formats. Sanitize output of binary content.

**Phabricator API Token Sent in HTTP POST Body:**
- Risk: API token is included in form data, not Authorization header. Logs may capture request body.
- Files: `phabricator_service.py:36-49`
- Current mitigation: HTTPS used, create-only scope
- Recommendations: Never log request body. Use Bearer token in header instead of form data. Rotate token regularly.

## Performance Bottlenecks

**Playwright Selector Testing Launches Full Browser Per Request:**
- Problem: Each `dtsa_playwright_selector` call launches headless Chromium, navigates to URL, tests selector, then shuts down browser. No browser reuse or caching.
- Files: `playwright_service.py:25-73`
- Cause: Browser is created fresh per call due to MCP stateless design. Navigation and rendering are slow (~5-10s per call).
- Improvement path: Consider persistent browser pool (if multiple tools can share state) or optimize to use lighter-weight DOM checking. Cache successful selector tests.

**Database Connection Pool Too Small:**
- Problem: Pool configured with only 3 connections and max 2 overflow
- Files: `dtsa_database.py:29-30`
- Cause: May cause connection exhaustion under concurrent load if multiple agents query simultaneously
- Improvement path: Monitor actual concurrency. Increase pool_size and max_overflow. Add connection pool monitoring/metrics.

**GitHub API Commit Filtering Limited to First 100 Results:**
- Problem: `github_service.py:184,200` requests per_page=100 and returns first 100, but GitHub API returns commits in reverse chronological order. Large time windows may need pagination.
- Files: `github_service.py:174-213`
- Cause: No pagination loop or "has more" indicator
- Improvement path: Implement pagination with `Link` header following. Document limitation in tool description.

**Grep Stops at 200 Matches Without Indication:**
- Problem: `filesystem_service.py:123` stops searching once 200 matches found. No indication to user that result is incomplete.
- Files: `filesystem_service.py:118-169`
- Cause: Hard limit to prevent memory bloat, but user doesn't know if more matches exist
- Improvement path: Return `matches_limited: true` or `match_limit_exceeded: true` in response. Suggest query refinement.

## Fragile Areas

**GitHub Service Falls Back to Local Repos Silently:**
- Files: `github_service.py:44-46,52-54`
- Why fragile: If both `DTSA_GITHUB_TOKEN` and `DTSA_LOCAL_REPOS_BASE` are unset, the service returns an error only after attempting to use local repos. If local repos base is misconfigured, user doesn't see clear guidance on which path to configure.
- Safe modification: Always validate that at least one source (GitHub token OR local repos base) is configured at startup. Fail early with clear message.
- Test coverage: No startup validation. No test for "both credentials missing" scenario.

**Filesystem Service Depends on OS Path Separator Logic:**
- Files: `filesystem_service.py:29-30`
- Why fragile: Uses `os.path.join()` which is Windows-aware, but `Path` objects internally handle separators differently. Mixed usage could cause path resolution bugs on Windows.
- Safe modification: Always use `Path` objects for all path operations, never mix with `os.path` functions.
- Test coverage: No cross-platform testing.

**MySQL Session Not Closed if Query Execution Timeout Occurs:**
- Files: `mysql_service.py:28-32`
- Why fragile: If `session.execute()` times out (max_execution_time=30s), the context manager still calls `session.close()`, but SQLAlchemy may not properly clean up the timed-out statement. Session may be left in a bad state in the pool.
- Safe modification: Explicitly call `session.rollback()` before close. Test timeout behavior.
- Test coverage: No tests for timeout scenarios.

**Phabricator Task Creation Assumes Specific Error Response Format:**
- Files: `phabricator_service.py:51-53`
- Why fragile: Checks for `data.get("error_code")` but doesn't validate response schema. If API response changes or is unexpected, error may not be caught.
- Safe modification: Validate full response structure, log full response on unexpected schema.
- Test coverage: No tests for various API failure modes.

## Scaling Limits

**Browser Pool Exhaustion Under Concurrent Load:**
- Current capacity: One browser instance per request, no pooling
- Limit: If 5+ `dtsa_playwright_selector` calls run in parallel, 5+ Chromium processes spawn. On resource-constrained systems, this causes CPU/memory spike and timeouts.
- Scaling path: Implement persistent browser pool with max connections. Queue requests with timeout. Document concurrency limits.

**Database Connection Pool Insufficient for Concurrent Agents:**
- Current capacity: 3 base connections, 2 overflow = 5 max concurrent
- Limit: If 10+ concurrent `dtsa_mysql_read` calls arrive from multiple agent instances, connections are exhausted
- Scaling path: Increase pool size dynamically based on load. Add connection queuing. Monitor pool saturation. Consider read replica load balancing.

**File Grep Stops at 200 Matches:**
- Current capacity: 200 matches per grep call
- Limit: Large repos with highly-matched patterns may return incomplete results
- Scaling path: Implement pagination. Document limit in tool description. Add `offset` parameter.

**GitHub API Rate Limits Not Handled:**
- Current capacity: 60 requests/hour unauthenticated, 5000/hour with token
- Limit: If multiple agents hammer GitHub API, rate limit headers are not checked. Requests fail silently.
- Scaling path: Check `X-RateLimit-*` headers. Implement backoff and retry logic. Cache recent commit queries.

## Dependencies at Risk

**Playwright Without Version Pin:**
- Risk: `playwright>=1.40.0` may introduce breaking changes. Browser binary version mismatch possible.
- Impact: Selector tests could suddenly fail if Playwright updates browser driver incompatibly
- Migration plan: Pin to specific minor version `playwright>=1.40.0,<1.50.0`. Test on version upgrades before deploying.

**MySQLConnector Connector Without Version Pin:**
- Risk: `mysql-connector-python>=9.0.0` is known to have protocol incompatibilities with different server versions
- Impact: Connection failures with specific database versions
- Migration plan: Pin to tested version. Test against all supported DB versions.

**GitPython Late-Imported Conditionally:**
- Risk: If neither GitHub token nor local repos are configured, GitPython is never imported, so missing dependency isn't caught
- Impact: User tries to use GitHub commits tool and gets cryptic import error
- Migration plan: Always import GitPython at startup. Fail fast if missing.

**httpx Async Client Not Pooled Across Requests:**
- Risk: Creating new client per request is inefficient. No connection reuse.
- Impact: GitHub and Phabricator tool calls are slower than necessary
- Migration plan: Create shared async client at module level or use context manager properly. Pool connections.

## Missing Critical Features

**No Request Authentication or Rate Limiting:**
- Problem: MCP tools are called directly by Claude with no authentication. No per-user rate limits or quota enforcement.
- Blocks: Cannot isolate usage per user. Cannot prevent abuse if credentials are leaked. No audit trail.
- Recommendation: Implement tool call filtering at MCP server level. Log caller identity. Enforce per-user or per-session quotas.

**No Observability or Metrics:**
- Problem: Only basic logging to stderr. No metrics (latency, error rates, pool utilization).
- Blocks: Cannot diagnose performance issues. Cannot detect when system is degrading.
- Recommendation: Add structured logging (JSON format). Export metrics (prometheus or cloudwatch). Add request tracing.

**No Graceful Shutdown or Timeout Management:**
- Problem: Server runs forever. If a tool call hangs (e.g., Playwright navigation timeout), it blocks the entire MCP server.
- Blocks: Long-running operations can starve other agents
- Recommendation: Implement global request timeout. Add graceful shutdown handler. Implement request queuing with timeout.

**No Caching or Memoization:**
- Problem: Repeated queries (same database query, same GitHub commits, same selectors) are executed every time
- Blocks: Unnecessary load on database and APIs. Slower tool response time.
- Recommendation: Add simple in-memory cache with TTL for frequent queries. Cache GitHub commits by repo+date range. Cache selector test results by URL.

## Test Coverage Gaps

**SQL Injection Prevention Not Tested:**
- What's not tested: Edge cases for SQL injection validation (multiline strings, comment syntax, parameterization)
- Files: `mysql_service.py:19-44`
- Risk: Malicious user could craft query that bypasses FORBIDDEN regex and executes non-SELECT statement
- Priority: High — blocks agent reliability and security

**Filesystem Sandbox Escape Not Tested:**
- What's not tested: Symlink traversal, relative path escapes, Unicode normalization bypasses
- Files: `filesystem_service.py:38-50`, `filesystem_service.py:172-209`
- Risk: Agent could read files outside configured repos base
- Priority: High — security boundary violation

**GitHub Service Fallback Logic Not Tested:**
- What's not tested: Behavior when both token and local repos are missing, when local repos don't exist, when GitHub API returns unexpected responses
- Files: `github_service.py:44-46,52-54,74-114,118-159,174-213,216-251`
- Risk: Unclear error messages, silent failures, wrong fallback chosen
- Priority: Medium — affects user experience and debugging

**Playwright Bot Detection Not Tested:**
- What's not tested: Various bot detection signatures, handling when different signatures appear, false positives
- Files: `playwright_service.py:10-18,45-56`
- Risk: Selector tests report false "blocked" status on legitimate sites
- Priority: Medium — affects tool accuracy

**Exception Handling Edge Cases Not Tested:**
- What's not tested: Timeout errors, connection reset, partial responses, malformed JSON
- Files: All service files
- Risk: Unexpected exceptions leak implementation details, confuse user
- Priority: Medium — debugging difficulty

**Phabricator API Failure Modes Not Tested:**
- What's not tested: Invalid token, missing fields in response, rate limiting, API version mismatch
- Files: `phabricator_service.py:18-64`
- Risk: Tasks created with incomplete data, unclear error messages
- Priority: Low — used infrequently

---

*Concerns audit: 2026-04-15*
