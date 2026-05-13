---
name: "DTAA Posts Channel"
description: "Posts channel exploratory analysis — sponsored posts (Facebook, LinkedIn, YouTube), counts, account breakdowns, annotation summaries. Activate for non-metric posts questions. For SOV/Reach/Frequency use /dtaa-posts-metrics instead."
---

# DTAA — Posts Channel (Exploratory)

## Channel Overview
- **Primary table**: `posts`
- **Platforms**: Facebook, LinkedIn, YouTube (sponsored posts)
- **Annotation entity type**: `POST`
- **Date column**: `web_contents.created` (via join — posts table has no direct date)
- **User join**: `posts` → `web_content_posts` → `web_contents` → `user_id`
- **Survey filter**: Apply `web_contents.user_wave_id IS NULL` (NOT on posts table)

## Table Schema (Key Columns)
```
posts: id, redirect_url, account_name, type (TINYINT), llm_annotation_status

web_content_posts: id, post_id (FK→posts.id), web_content_id (FK→web_contents.id)
  -- This is the bridge table for user_id and dates
```

## Standard Join Pattern
```sql
FROM posts p
JOIN web_content_posts wcp ON wcp.post_id = p.id
JOIN web_contents wc ON wcp.web_content_id = wc.id
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = p.id AND ga.entity_type = 'POST'
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
```

## Brand/Disease Annotation Joins
```sql
-- Add brands:
JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN brand_terms bt ON gab.brand_id = bt.id

-- Add diseases (LEFT JOIN — no disease = TA agnostic):
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN disease_terms dt ON gad.disease_id = dt.id
```

## Common Query Patterns

### Total post count by date range
```sql
SELECT COUNT(DISTINCT p.id) AS total_posts, COUNT(DISTINCT wc.user_id) AS unique_users
FROM posts p
JOIN web_content_posts wcp ON wcp.post_id = p.id
JOIN web_contents wc ON wcp.web_content_id = wc.id
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30);
```

### Posts by brand
```sql
SELECT bt.standard_name AS brand, COUNT(DISTINCT p.id) AS post_count
FROM posts p
JOIN web_content_posts wcp ON wcp.post_id = p.id
JOIN web_contents wc ON wcp.web_content_id = wc.id
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = p.id AND ga.entity_type = 'POST'
JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN brand_terms bt ON gab.brand_id = bt.id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
GROUP BY bt.standard_name
ORDER BY post_count DESC;
```

### Posts by account name (publisher)
```sql
SELECT p.account_name, COUNT(DISTINCT p.id) AS post_count
FROM posts p
JOIN web_content_posts wcp ON wcp.post_id = p.id
JOIN web_contents wc ON wcp.web_content_id = wc.id
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY p.account_name
ORDER BY post_count DESC;
```

### Monthly post trend
```sql
SELECT DATE_FORMAT(wc.created, '%Y-%m') AS month, COUNT(DISTINCT p.id) AS post_count
FROM posts p
JOIN web_content_posts wcp ON wcp.post_id = p.id
JOIN web_contents wc ON wcp.web_content_id = wc.id
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY month
ORDER BY month;
```

## References
- Full schema: `dtaa/references/schema.md`
- SQL guidelines: `dtaa/references/guidelines.md`
- Common patterns: `references/query_patterns.md`
