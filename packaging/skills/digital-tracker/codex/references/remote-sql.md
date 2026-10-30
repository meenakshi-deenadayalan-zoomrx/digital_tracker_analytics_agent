# Native Perxcept SQL contract

Read this before discovery or executing any SQL template in this package.

- Use server `prod-perxcept-mysql-mcp`, tool `perxcept_execute_sql`. Its declared endpoint is `https://prod-px-mysql-mcp-toolbox.zoomrx.dev/mcp`; authentication is the client's native Entra OAuth, not a local DB username/password.
- The authenticated tool catalog has one required input: `{ "sql": "SELECT ... LIMIT 50" }`. It exposes no parameter-binding, max_rows, export or pagination arguments. Successful rows are individual JSON text content items; an empty result is an empty content array. Check MCP errors before interpreting rows, parse every returned JSON row, and never treat prose/errors as data. Native catalog/schema discovery remains the authority if the service changes.
- Qualify each physical application table as `perxcept_extension.table` for the existing analytics/diagnostic templates. The server default is `perxcept_crawler`, so bare table names change the source. Use crawler or archive schemas only when explicitly investigating that source and after schema discovery; never silently substitute archive data.
- Every executed query needs an outer `LIMIT` (start with 50), only required output columns, and an indexed or date filter. Apply this even to scalar aggregates and schema discovery. Channel templates are building blocks: materialize the confirmed dates/IDs and mandatory quality filters before execution. A fragment or a deliberately marked incorrect example is never a ready query.
- Keep a metric's full confirmed population inside its aggregates. Apply the result LIMIT after the final aggregate, not inside the denominator, user cohort, brand normalization, or window. Do not calculate shares from a truncated top-N set.
- A result at the requested limit, a server truncation flag, missing rows, or a shortened payload is incomplete evidence. Use deterministic keyset pagination over the final unique grouping keys, preserve the same confirmed filters and population, deduplicate, and reconcile an independent grouped count. If consistency/completeness cannot be established, stop and label incomplete; no fabricated totals or shares.
- Entity lookup tables use their indexed ID as a cursor plus the requested name pattern; keep paging until the candidate set is complete before presenting ALL alternatives. Date-based tables use the confirmed date column and interval. For unbounded project listings, ask for a scope or explicitly page over the indexed project ID.
- SQL templates use placeholders; these are not sent literally. Use bound parameters only if the discovered schema supports them. Otherwise use validated numeric IDs, canonical UTC dates, and SQL string literals encoded as UTF-8 hex expressions (`CONVERT(0x... USING utf8mb4)`) for user-supplied strings, never raw concatenation. Table/column identifiers come from reviewed references or schema discovery, never a user string. If safe materialization is unavailable, request the supported tool contract rather than execute unsafe SQL.
- SELECT only. The native read-only WITH/SELECT compatibility probe succeeded on 2026-10-09; existing CTE and nested-subquery metric equivalents remain available; no DB writes, DDL, stored procedures, local driver, Vault/Jenkins refresh, browser cookie extraction or fallback to retired `dtaa-tools`/DB workers.
- Normal skill entity confirmation and privacy rules still apply. Native MCP authentication or native sandbox startup failure is reported separately from a SQL/data finding. Existing M365, Synapse API and AP sessions are preserved.

## Read-only connection acceptance

Discover `perxcept_execute_sql`, complete initial native Entra authorization if requested, then call `SELECT 1 AS connection_ok LIMIT 1`. After it succeeds, query a bounded metadata page such as:

`SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema IN ('perxcept_extension','perxcept_crawler') ORDER BY table_schema, table_name LIMIT 50`.

Connection success does not prove metric correctness, complete pagination, selector execution, local file access, or fleet rollout readiness.
