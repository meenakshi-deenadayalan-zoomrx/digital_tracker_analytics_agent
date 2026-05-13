# Volume Query Patterns by Channel

All queries use `%(start)s` / `%(end)s` parameters. Run for current, -7d, and -28d windows.

## web_contents
```sql
SELECT DATE(visited_timestamp) AS dt, COUNT(*) AS cnt
FROM web_contents
WHERE visited_timestamp BETWEEN %(start)s AND %(end)s
GROUP BY dt ORDER BY dt;
```

## ads
```sql
SELECT DATE(created_at) AS dt, COUNT(*) AS cnt
FROM ads
WHERE created_at BETWEEN %(start)s AND %(end)s
GROUP BY dt ORDER BY dt;
```

## email
```sql
SELECT DATE(wc.visited_timestamp) AS dt, COUNT(*) AS cnt
FROM web_contents wc
JOIN emails e ON wc.id = e.web_content_id
WHERE wc.visited_timestamp BETWEEN %(start)s AND %(end)s
GROUP BY dt ORDER BY dt;
```

## search_results
```sql
SELECT DATE(sq.created_at) AS dt, COUNT(*) AS cnt
FROM search_queries sq
WHERE sq.created_at BETWEEN %(start)s AND %(end)s
GROUP BY dt ORDER BY dt;
```

## social_posts
```sql
SELECT DATE(created_at) AS dt, COUNT(*) AS cnt
FROM posts
WHERE created_at BETWEEN %(start)s AND %(end)s
GROUP BY dt ORDER BY dt;
```

## Cross-platform breakdown (any channel)
```sql
SELECT DATE(wc.visited_timestamp) AS dt, c.device_type, COUNT(*) AS cnt
FROM web_contents wc
JOIN clients c ON wc.client_id = c.id
WHERE wc.visited_timestamp BETWEEN %(start)s AND %(end)s
GROUP BY dt, c.device_type ORDER BY dt;
```

## Background request status
```sql
SELECT type, status, COUNT(*) AS cnt
FROM background_requests
WHERE created_at BETWEEN %(start)s AND %(end)s
GROUP BY type, status ORDER BY type;
```

## Active users
```sql
SELECT DATE(c.last_request) AS dt, COUNT(DISTINCT c.user_id) AS active_users
FROM clients c
WHERE c.last_request BETWEEN %(start)s AND %(end)s
  AND c.is_data_collectable = 1
GROUP BY dt ORDER BY dt;
```

## AI responses (search_results channel)
```sql
SELECT DATE(created_at) AS dt, response_type, COUNT(*) AS cnt
FROM ai_responses
WHERE created_at BETWEEN %(start)s AND %(end)s
GROUP BY dt, response_type ORDER BY dt;
```
