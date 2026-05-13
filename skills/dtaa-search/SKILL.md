---
name: "DTAA Search Channel"
description: "Search results and search queries exploratory analysis — sponsored search ads, organic results, AI references, search terms, engine breakdown. Activate for non-metric search questions. For SOV/Reach/Frequency use /dtaa-search-metrics instead."
---

# DTAA — Search Channel (Exploratory)

## Channel Overview
- **Primary tables**: `search_results` + `search_queries`
- **Date column**: `search_results.created` / `search_queries.created`
- **Type filters**:
  - `SPONSORED_AD` = paid search ads (entity_type: `SEARCH_AD`)
  - `ORGANIC` = unpaid organic results (entity_type: `SEARCH_RESULT`)
  - `AI_REFERENCE` = links in AI responses (entity_type: `SEARCH_RESULT`)
- **Mandatory user filter**: speciality_id NOT IN (28, 30)
- **Note**: `search_results` has no `user_wave_id`; apply on `search_queries` if joined

## Table Schema (Key Columns)
```
search_results: id, search_query_id (FK→search_queries.id), title, description,
                redirect_url, rank, tracked_url_id, created, is_branded,
                user_id, client_id, page_number,
                type (SPONSORED_AD/ORGANIC/AI_REFERENCE), is_clicked

search_queries: id, search_query, is_branded, user_id, client_id,
                engine_type (BING/GOOGLE), timezone, timestamp, created,
                user_wave_id, parent_query_id,
                ai_mode_engaged, ai_mode_duration, is_show_more_clicked
```

## Standard Join Pattern

### For search results (ads/organic):
```sql
FROM search_results sr
JOIN user_speciality_mappings usm ON sr.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = sr.id
    AND ga.entity_type = CASE
        WHEN sr.type = 'SPONSORED_AD' THEN 'SEARCH_AD'
        ELSE 'SEARCH_RESULT'
    END
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND sr.type IN (...)  -- filter by type
```

### For search queries:
```sql
FROM search_queries sq
JOIN user_speciality_mappings usm ON sq.user_id = usm.user_id
WHERE sq.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND sq.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
```

## Brand/Disease Annotation Joins
```sql
-- Add brands:
JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN brand_terms bt ON gab.brand_id = bt.id

-- Add diseases:
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN disease_terms dt ON gad.disease_id = dt.id
```

## Common Query Patterns

### Total search results count by type
```sql
SELECT sr.type, COUNT(DISTINCT sr.id) AS result_count, COUNT(DISTINCT sr.user_id) AS unique_users
FROM search_results sr
JOIN user_speciality_mappings usm ON sr.user_id = usm.user_id
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY sr.type;
```

### Search results by brand (any type)
```sql
SELECT bt.standard_name AS brand, sr.type, COUNT(DISTINCT sr.id) AS result_count
FROM search_results sr
JOIN user_speciality_mappings usm ON sr.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = sr.id
    AND ga.entity_type = IF(sr.type = 'SPONSORED_AD', 'SEARCH_AD', 'SEARCH_RESULT')
JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN brand_terms bt ON gab.brand_id = bt.id
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
GROUP BY bt.standard_name, sr.type
ORDER BY result_count DESC;
```

### Search queries by engine
```sql
SELECT sq.engine_type, COUNT(DISTINCT sq.id) AS query_count, COUNT(DISTINCT sq.user_id) AS unique_users
FROM search_queries sq
JOIN user_speciality_mappings usm ON sq.user_id = usm.user_id
WHERE sq.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND sq.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY sq.engine_type;
```

### Branded vs non-branded searches
```sql
SELECT sq.is_branded, COUNT(DISTINCT sq.id) AS query_count
FROM search_queries sq
JOIN user_speciality_mappings usm ON sq.user_id = usm.user_id
WHERE sq.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND sq.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY sq.is_branded;
```

### AI mode engagement
```sql
SELECT
    SUM(sq.ai_mode_engaged) AS ai_mode_queries,
    COUNT(DISTINCT sq.id) AS total_queries,
    ROUND(SUM(sq.ai_mode_engaged) / COUNT(DISTINCT sq.id) * 100, 2) AS ai_mode_pct
FROM search_queries sq
JOIN user_speciality_mappings usm ON sq.user_id = usm.user_id
WHERE sq.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND sq.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30);
```

### Click-through rate on search results
```sql
SELECT
    SUM(sr.is_clicked) AS clicked,
    COUNT(sr.id) AS total_results,
    ROUND(SUM(sr.is_clicked) / COUNT(sr.id) * 100, 2) AS ctr_pct
FROM search_results sr
JOIN user_speciality_mappings usm ON sr.user_id = usm.user_id
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND sr.type = '{type}';  -- SPONSORED_AD / ORGANIC / AI_REFERENCE
```

## References
- Full schema: `dtaa/references/schema.md`
- SQL guidelines: `dtaa/references/guidelines.md`
- Common patterns: `references/query_patterns.md`
