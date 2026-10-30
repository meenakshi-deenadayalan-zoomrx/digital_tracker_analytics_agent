
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
FROM perxcept_extension.posts p
JOIN perxcept_extension.web_content_posts wcp ON wcp.post_id = p.id
JOIN perxcept_extension.web_contents wc ON wcp.web_content_id = wc.id
JOIN perxcept_extension.user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = p.id AND ga.entity_type = 'POST'
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
```

## Brand/Disease Annotation Joins
```sql
-- Add brands:
JOIN perxcept_extension.gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN perxcept_extension.brand_terms bt ON gab.brand_id = bt.id

-- Add diseases (LEFT JOIN — no disease = TA agnostic):
LEFT JOIN perxcept_extension.gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN perxcept_extension.disease_terms dt ON gad.disease_id = dt.id
```

## Common Query Patterns

### Total post count by date range
```sql
SELECT COUNT(DISTINCT p.id) AS total_posts, COUNT(DISTINCT wc.user_id) AS unique_users
FROM perxcept_extension.posts p
JOIN perxcept_extension.web_content_posts wcp ON wcp.post_id = p.id
JOIN perxcept_extension.web_contents wc ON wcp.web_content_id = wc.id
JOIN perxcept_extension.user_speciality_mappings usm ON wc.user_id = usm.user_id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
LIMIT 50;
```

### Posts by brand
```sql
SELECT bt.standard_name AS brand, COUNT(DISTINCT p.id) AS post_count
FROM perxcept_extension.posts p
JOIN perxcept_extension.web_content_posts wcp ON wcp.post_id = p.id
JOIN perxcept_extension.web_contents wc ON wcp.web_content_id = wc.id
JOIN perxcept_extension.user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = p.id AND ga.entity_type = 'POST'
JOIN perxcept_extension.gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN perxcept_extension.brand_terms bt ON gab.brand_id = bt.id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
GROUP BY bt.standard_name
ORDER BY post_count DESC
LIMIT 50;
```

### Posts by account name (publisher)
```sql
SELECT p.account_name, COUNT(DISTINCT p.id) AS post_count
FROM perxcept_extension.posts p
JOIN perxcept_extension.web_content_posts wcp ON wcp.post_id = p.id
JOIN perxcept_extension.web_contents wc ON wcp.web_content_id = wc.id
JOIN perxcept_extension.user_speciality_mappings usm ON wc.user_id = usm.user_id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY p.account_name
ORDER BY post_count DESC
LIMIT 50;
```

### Monthly post trend
```sql
SELECT DATE_FORMAT(wc.created, '%Y-%m') AS month, COUNT(DISTINCT p.id) AS post_count
FROM perxcept_extension.posts p
JOIN perxcept_extension.web_content_posts wcp ON wcp.post_id = p.id
JOIN perxcept_extension.web_contents wc ON wcp.web_content_id = wc.id
JOIN perxcept_extension.user_speciality_mappings usm ON wc.user_id = usm.user_id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY month
ORDER BY month
LIMIT 50;
```

## References
- Full schema: `references/schema.md`
- SQL guidelines: `references/guidelines.md`

## Extended Query Patterns

# Posts Channel — Additional Query Patterns

## Posts by Disease
```sql
SELECT dt.standard_name AS disease, COUNT(DISTINCT p.id) AS post_count
FROM perxcept_extension.posts p
JOIN perxcept_extension.web_content_posts wcp ON wcp.post_id = p.id
JOIN perxcept_extension.web_contents wc ON wcp.web_content_id = wc.id
JOIN perxcept_extension.user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = p.id AND ga.entity_type = 'POST'
LEFT JOIN perxcept_extension.gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN perxcept_extension.disease_terms dt ON gad.disease_id = dt.id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND dt.standard_name IS NOT NULL
GROUP BY dt.standard_name
ORDER BY post_count DESC
LIMIT 50;
```

## Posts by Manufacturer
```sql
SELECT mt.standard_name AS manufacturer, COUNT(DISTINCT p.id) AS post_count
FROM perxcept_extension.posts p
JOIN perxcept_extension.web_content_posts wcp ON wcp.post_id = p.id
JOIN perxcept_extension.web_contents wc ON wcp.web_content_id = wc.id
JOIN perxcept_extension.user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = p.id AND ga.entity_type = 'POST'
JOIN perxcept_extension.gpt_annotations_manufacturers gam ON ga.id = gam.gpt_annotation_id
JOIN perxcept_extension.manufacturer_terms mt ON gam.manufacturer_id = mt.id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY mt.standard_name
ORDER BY post_count DESC
LIMIT 50;
```

## Posts with Media
```sql
SELECT p.id, p.account_name, m.source_url
FROM perxcept_extension.posts p
JOIN perxcept_extension.web_content_posts wcp ON wcp.post_id = p.id
JOIN perxcept_extension.web_contents wc ON wcp.web_content_id = wc.id
JOIN perxcept_extension.user_speciality_mappings usm ON wc.user_id = usm.user_id
LEFT JOIN perxcept_extension.media m ON m.entity_id = p.id AND m.entity_type = 'POST'
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
LIMIT 50;
```

## Healthcare vs Non-Healthcare Posts
```sql
SELECT
    SUM(CASE WHEN ga.is_healthcare_relevant = 1 THEN 1 ELSE 0 END) AS healthcare_posts,
    SUM(CASE WHEN ga.is_healthcare_relevant = 0 THEN 1 ELSE 0 END) AS non_healthcare_posts
FROM perxcept_extension.posts p
JOIN perxcept_extension.web_content_posts wcp ON wcp.post_id = p.id
JOIN perxcept_extension.web_contents wc ON wcp.web_content_id = wc.id
JOIN perxcept_extension.user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = p.id AND ga.entity_type = 'POST'
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
LIMIT 50;
```
