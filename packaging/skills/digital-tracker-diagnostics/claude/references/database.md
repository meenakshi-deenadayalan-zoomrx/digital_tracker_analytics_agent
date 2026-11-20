
# Database Investigation

Use `perxcept_execute_sql` on the native Perxcept MCP; explicitly qualify the extension database. Read `references/remote-sql.md` first.

## Hard Rules

1. **SELECT only** — INSERT/UPDATE/DELETE/DROP are rejected
2. **Aggregates only** — `COUNT(*)`, `GROUP BY`; never request raw rows (PII risk)
3. **Max 100 rows** — use date ranges and `GROUP BY` to stay within limits
4. **Safe query arguments** — placeholders below are templates, not literal remote arguments. Follow `references/remote-sql.md` and the actual tool input schema; never concatenate raw user strings.
5. **3 windows always** — current period, 1 week prior, 4 weeks prior

## Key Tables

| Table | Primary Use | Key Columns |
|---|---|---|
| `web_contents` | Page visit volumes | `visited_timestamp`, `client_id`, `status`, `type` |
| `ads` | Ad capture volumes | `created`, `client_id`, `user_wave_id` |
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

See the **Volume Query Patterns** section below for pre-built queries for each channel.

### Baseline comparison (always run all 3)
```sql
-- Current period
SELECT DATE(visited_timestamp) AS dt, COUNT(*) AS cnt
FROM perxcept_extension.web_contents
WHERE visited_timestamp BETWEEN %(start)s AND %(end)s
GROUP BY dt ORDER BY dt;

-- 1-week baseline: subtract 7 days from start/end
-- 4-week baseline: subtract 28 days from start/end
LIMIT 50;
```

### Platform breakdown
```sql
SELECT DATE(wc.visited_timestamp) AS dt, c.device_type, COUNT(*) AS cnt
FROM perxcept_extension.web_contents wc
JOIN perxcept_extension.clients c ON wc.client_id = c.id
WHERE wc.visited_timestamp BETWEEN %(start)s AND %(end)s
GROUP BY dt, c.device_type ORDER BY dt
LIMIT 50;
```

## Volume Classification

| Pattern | Classification |
|---|---|
| Current = 0, baseline > 0 | `HARD_STOP` |
| Current < 50% of baseline | `SEVERE_DEGRADATION` |
| Current 50–80% of baseline | `PARTIAL_DEGRADATION` |
| Current ≈ baseline (±20%) | `NORMAL` — stop, return data to PO |
| Drop only on specific days | `DOW_EFFECT` — likely not a bug |

## Volume Query Patterns

# Volume Query Patterns by Channel

All queries use `%(start)s` / `%(end)s` parameters. Run for current, -7d, and -28d windows.

## web_contents
```sql
SELECT DATE(visited_timestamp) AS dt, COUNT(*) AS cnt
FROM perxcept_extension.web_contents
WHERE visited_timestamp BETWEEN %(start)s AND %(end)s
GROUP BY dt ORDER BY dt
LIMIT 50;
```

## ads
```sql
SELECT DATE(created) AS dt, COUNT(*) AS cnt
FROM perxcept_extension.ads
WHERE created BETWEEN %(start)s AND %(end)s
GROUP BY dt ORDER BY dt
LIMIT 50;
```

## email
```sql
SELECT DATE(wc.visited_timestamp) AS dt, COUNT(*) AS cnt
FROM perxcept_extension.web_contents wc
JOIN perxcept_extension.emails e ON wc.id = e.web_content_id
WHERE wc.visited_timestamp BETWEEN %(start)s AND %(end)s
GROUP BY dt ORDER BY dt
LIMIT 50;
```

## search_results
```sql
SELECT DATE(sq.created_at) AS dt, COUNT(*) AS cnt
FROM perxcept_extension.search_queries sq
WHERE sq.created_at BETWEEN %(start)s AND %(end)s
GROUP BY dt ORDER BY dt
LIMIT 50;
```

## social_posts
```sql
SELECT DATE(created_at) AS dt, COUNT(*) AS cnt
FROM perxcept_extension.posts
WHERE created_at BETWEEN %(start)s AND %(end)s
GROUP BY dt ORDER BY dt
LIMIT 50;
```

## Cross-platform breakdown (any channel)
```sql
SELECT DATE(wc.visited_timestamp) AS dt, c.device_type, COUNT(*) AS cnt
FROM perxcept_extension.web_contents wc
JOIN perxcept_extension.clients c ON wc.client_id = c.id
WHERE wc.visited_timestamp BETWEEN %(start)s AND %(end)s
GROUP BY dt, c.device_type ORDER BY dt
LIMIT 50;
```

## Background request status
```sql
SELECT type, status, COUNT(*) AS cnt
FROM perxcept_extension.background_requests
WHERE created_at BETWEEN %(start)s AND %(end)s
GROUP BY type, status ORDER BY type
LIMIT 50;
```

## Active users
```sql
SELECT DATE(c.last_request) AS dt, COUNT(DISTINCT c.user_id) AS active_users
FROM perxcept_extension.clients c
WHERE c.last_request BETWEEN %(start)s AND %(end)s
  AND c.is_data_collectable = 1
GROUP BY dt ORDER BY dt
LIMIT 50;
```

## AI responses (search_results channel)
```sql
SELECT DATE(created_at) AS dt, response_type, COUNT(*) AS cnt
FROM perxcept_extension.ai_responses
WHERE created_at BETWEEN %(start)s AND %(end)s
GROUP BY dt, response_type ORDER BY dt
LIMIT 50;
```

## Verified schema compatibility

Read `references/schema-live-check.md` before using these historical patterns. It records exact live supported columns and blocks missing/ambiguous columns or sources; do not auto-map timestamps.
