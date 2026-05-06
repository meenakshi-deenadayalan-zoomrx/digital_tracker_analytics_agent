---
name: "DTAA Web Contents Channel"
description: "Web contents channel exploratory analysis — page visits, URL categories, duration, annotation summaries. Activate for non-metric web questions. For Share of Attention/Reach/Frequency use /dtaa-web-metrics instead."
---

# DTAA — Web Contents Channel (Exploratory)

## Channel Overview
- **Primary table**: `web_contents`
- **Mandatory type filter**: `type IN ('WEB_PAGE', 'HTML_WEB_PAGE')`
- **Date column**: `created`
- **Annotation entity type**: `WEB_CONTENT_GROUP` (NOT web_contents directly)
- **Annotation join path**: `web_contents.web_content_group_id` → `web_content_groups.id` → `gpt_annotations`

## Table Schema (Key Columns)
```
web_contents: id, user_id, absolute_url, duration (TIME), visited_timestamp,
              created, status, type (WEB_PAGE/EMAIL_CAMPAIGN/AD_SOURCE_URL/HTML_WEB_PAGE/POST),
              timezone, closed_timestamp, tracked_url_id, session, client_id,
              web_content_group_id, user_wave_id
```

## Critical: Annotation Join Pattern (Different from other channels)
```sql
FROM web_contents wc
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN web_content_groups wcg ON wc.web_content_group_id = wcg.id
JOIN gpt_annotations ga ON ga.entity_id = wcg.id AND ga.entity_type = 'WEB_CONTENT_GROUP'
WHERE wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
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

-- Add brand-disease weights (for Share of Attention only):
LEFT JOIN gpt_annotations_diseases_brands gadb
    ON ga.id = gadb.gpt_annotation_id
    AND gadb.brand_id = gab.brand_id
    AND gadb.disease_id = gad.disease_id
```

## URL Classification
```sql
-- Get website category and brand association for visited pages
LEFT JOIN tracked_urls tu ON wc.tracked_url_id = tu.id
-- tu.category: ENUM for site category
-- tu.is_interested_domain: 1 = in whitelist
-- tu.brand_id: brand associated with domain
```

## Common Query Patterns

> **MANDATORY — Project Target List Filter**: When a project or client context is provided, ALL queries MUST restrict to project target list users. Omitting this returns data for all users in the system, not just the client's target audience — results will be wrong for client reports.
> ```sql
> JOIN users u ON wc.user_id = u.id
> JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
> ```
> Add these joins immediately after `FROM web_contents wc` in every query below when `project_id` is known.

### Total page visits by date range
```sql
SELECT COUNT(DISTINCT wc.id) AS total_visits, COUNT(DISTINCT wc.user_id) AS unique_users
FROM web_contents wc
JOIN users u ON wc.user_id = u.id
JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30);
```

### Top visited websites
```sql
SELECT tu.url AS website, COUNT(DISTINCT wc.id) AS visit_count,
       COUNT(DISTINCT wc.user_id) AS unique_users
FROM web_contents wc
JOIN users u ON wc.user_id = u.id
JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
LEFT JOIN tracked_urls tu ON wc.tracked_url_id = tu.id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY tu.url
ORDER BY visit_count DESC;
```

### Page visits by brand
```sql
SELECT bt.standard_name AS brand, COUNT(DISTINCT wc.id) AS visit_count
FROM web_contents wc
JOIN users u ON wc.user_id = u.id
JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN web_content_groups wcg ON wc.web_content_group_id = wcg.id
JOIN gpt_annotations ga ON ga.entity_id = wcg.id AND ga.entity_type = 'WEB_CONTENT_GROUP'
JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN brand_terms bt ON gab.brand_id = bt.id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
GROUP BY bt.standard_name
ORDER BY visit_count DESC;
```

### Average time spent per brand (total duration)
```sql
SELECT bt.standard_name AS brand,
       SEC_TO_TIME(SUM(TIME_TO_SEC(wc.duration))) AS total_duration,
       COUNT(DISTINCT wc.user_id) AS unique_users
FROM web_contents wc
JOIN users u ON wc.user_id = u.id
JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN web_content_groups wcg ON wc.web_content_group_id = wcg.id
JOIN gpt_annotations ga ON ga.entity_id = wcg.id AND ga.entity_type = 'WEB_CONTENT_GROUP'
JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN brand_terms bt ON gab.brand_id = bt.id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY bt.standard_name
ORDER BY total_duration DESC;
```

## References
- Full schema: `dtaa/references/schema.md`
- SQL guidelines: `dtaa/references/guidelines.md`
- Common patterns: `references/query_patterns.md`
