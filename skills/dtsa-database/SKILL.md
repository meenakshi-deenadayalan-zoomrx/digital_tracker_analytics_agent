---
name: "DTSA Database Investigation"
description: "Extension MySQL database knowledge for the Digital Tracker. Activate when verifying tracking volumes, checking data quality, querying user/client state, or running baseline comparisons against the Perxcept extension read replica."
---

# Database Investigation

Use `dtsa_mysql_read` to query the Perxcept extension MySQL read replica.

## Hard Rules

1. **SELECT only** — INSERT/UPDATE/DELETE/DROP are rejected
2. **Aggregates only** — `COUNT(*)`, `GROUP BY`; never request raw rows (PII risk)
3. **Max 100 rows** — use date ranges and `GROUP BY` to stay within limits
4. **Parameterized queries** — use `%(param)s` placeholders, never string concatenation
5. **3 windows always** — current period, 1 week prior, 4 weeks prior

## Key Tables

| Table | Primary Use | Key Columns |
|---|---|---|
| `web_contents` | Page visit volumes | `visited_timestamp`, `client_id`, `status`, `type` |
| `ads` | Ad capture volumes | `created_at`, `client_id`, `status` |
| `emails` | Email capture volumes | `web_content_id`, `email_provider`, `created_at` |
| `search_queries` | SERP volumes | `created_at`, `engine_type`, `ai_mode_engaged` |
| `search_results` | Search result rows | `search_query_id`, `is_paid`, `position` |
| `ai_responses` | AI Overview / AI Mode | `search_query_id`, `response_type`, `llm_annotation_status` |
| `posts` | Social post volumes | `created_at`, `is_sponsored` |
| `clients` | Device/platform info | `device_type`, `device_platform`, `last_request` |
| `users` | User state | `flags`, `allow_tracking` |
| `background_requests` | Async task status | `type`, `status`, `retry` |
| `ad_server_domains` | Ad domain whitelist | `domain` |
| `ad_ignorelist_domains` | Ad destination blacklist | `domain` |
| `visited_domains` | Domain healthcare cache | `domain`, `is_healthcare` |

Full schema: `dtsa_read_file("perxcept-ap-server/docs/09-database-reference-extension.md")`

## Volume Query Patterns

See `references/volume_query_patterns.md` for pre-built queries for each channel.

### Baseline comparison (always run all 3)
```sql
-- Current period
SELECT DATE(visited_timestamp) AS dt, COUNT(*) AS cnt
FROM web_contents
WHERE visited_timestamp BETWEEN %(start)s AND %(end)s
GROUP BY dt ORDER BY dt;

-- 1-week baseline: subtract 7 days from start/end
-- 4-week baseline: subtract 28 days from start/end
```

### Platform breakdown
```sql
SELECT DATE(wc.visited_timestamp) AS dt, c.device_type, COUNT(*) AS cnt
FROM web_contents wc
JOIN clients c ON wc.client_id = c.id
WHERE wc.visited_timestamp BETWEEN %(start)s AND %(end)s
GROUP BY dt, c.device_type ORDER BY dt;
```

## Volume Classification

| Pattern | Classification |
|---|---|
| Current = 0, baseline > 0 | `HARD_STOP` |
| Current < 50% of baseline | `SEVERE_DEGRADATION` |
| Current 50–80% of baseline | `PARTIAL_DEGRADATION` |
| Current ≈ baseline (±20%) | `NORMAL` — stop, return data to PO |
| Drop only on specific days | `DOW_EFFECT` — likely not a bug |
