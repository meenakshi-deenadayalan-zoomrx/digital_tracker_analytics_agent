
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
FROM perxcept_extension.search_results sr
JOIN perxcept_extension.user_speciality_mappings usm ON sr.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = sr.id
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
FROM perxcept_extension.search_queries sq
JOIN perxcept_extension.user_speciality_mappings usm ON sq.user_id = usm.user_id
WHERE sq.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND sq.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
```

## Brand/Disease Annotation Joins
```sql
-- Add brands:
JOIN perxcept_extension.gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN perxcept_extension.brand_terms bt ON gab.brand_id = bt.id

-- Add diseases:
LEFT JOIN perxcept_extension.gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN perxcept_extension.disease_terms dt ON gad.disease_id = dt.id
```

## Common Query Patterns

### Total search results count by type
```sql
SELECT sr.type, COUNT(DISTINCT sr.id) AS result_count, COUNT(DISTINCT sr.user_id) AS unique_users
FROM perxcept_extension.search_results sr
JOIN perxcept_extension.user_speciality_mappings usm ON sr.user_id = usm.user_id
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY sr.type
LIMIT 50;
```

### Search results by brand (any type)
```sql
SELECT bt.standard_name AS brand, sr.type, COUNT(DISTINCT sr.id) AS result_count
FROM perxcept_extension.search_results sr
JOIN perxcept_extension.user_speciality_mappings usm ON sr.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = sr.id
    AND ga.entity_type = IF(sr.type = 'SPONSORED_AD', 'SEARCH_AD', 'SEARCH_RESULT')
JOIN perxcept_extension.gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN perxcept_extension.brand_terms bt ON gab.brand_id = bt.id
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
GROUP BY bt.standard_name, sr.type
ORDER BY result_count DESC
LIMIT 50;
```

### Search queries by engine
```sql
SELECT sq.engine_type, COUNT(DISTINCT sq.id) AS query_count, COUNT(DISTINCT sq.user_id) AS unique_users
FROM perxcept_extension.search_queries sq
JOIN perxcept_extension.user_speciality_mappings usm ON sq.user_id = usm.user_id
WHERE sq.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND sq.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY sq.engine_type
LIMIT 50;
```

### Branded vs non-branded searches
```sql
SELECT sq.is_branded, COUNT(DISTINCT sq.id) AS query_count
FROM perxcept_extension.search_queries sq
JOIN perxcept_extension.user_speciality_mappings usm ON sq.user_id = usm.user_id
WHERE sq.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND sq.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY sq.is_branded
LIMIT 50;
```

### AI mode engagement
```sql
SELECT
    SUM(sq.ai_mode_engaged) AS ai_mode_queries,
    COUNT(DISTINCT sq.id) AS total_queries,
    ROUND(SUM(sq.ai_mode_engaged) / COUNT(DISTINCT sq.id) * 100, 2) AS ai_mode_pct
FROM perxcept_extension.search_queries sq
JOIN perxcept_extension.user_speciality_mappings usm ON sq.user_id = usm.user_id
WHERE sq.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND sq.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
LIMIT 50;
```

### Click-through rate on search results
```sql
SELECT
    SUM(sr.is_clicked) AS clicked,
    COUNT(sr.id) AS total_results,
    ROUND(SUM(sr.is_clicked) / COUNT(sr.id) * 100, 2) AS ctr_pct
FROM perxcept_extension.search_results sr
JOIN perxcept_extension.user_speciality_mappings usm ON sr.user_id = usm.user_id
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND sr.type = '{type}';  -- SPONSORED_AD / ORGANIC / AI_REFERENCE
LIMIT 50;
```

## References
- Full schema: `references/schema.md`
- SQL guidelines: `references/guidelines.md`

## Extended Query Patterns

# Search Channel — Additional Query Patterns

## Search Queries with AI Responses
```sql
SELECT sq.id, sq.search_query, ar.response_type, ar.llm_annotation_status
FROM perxcept_extension.search_queries sq
JOIN perxcept_extension.user_speciality_mappings usm ON sq.user_id = usm.user_id
LEFT JOIN perxcept_extension.ai_responses ar ON ar.search_query_id = sq.id
WHERE sq.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND sq.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND ar.id IS NOT NULL  -- only queries with AI responses
LIMIT 50;
```

## Search Results by Rank (Position Analysis)
```sql
SELECT sr.rank, COUNT(DISTINCT sr.id) AS result_count,
       COUNT(DISTINCT sr.user_id) AS unique_users
FROM perxcept_extension.search_results sr
JOIN perxcept_extension.user_speciality_mappings usm ON sr.user_id = usm.user_id
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND sr.type = '{type}'
GROUP BY sr.rank
ORDER BY sr.rank
LIMIT 50;
```

## Brand Presence in Organic vs Paid Search
```sql
SELECT
    bt.standard_name AS brand,
    SUM(CASE WHEN sr.type = 'SPONSORED_AD' THEN 1 ELSE 0 END) AS paid_count,
    SUM(CASE WHEN sr.type = 'ORGANIC' THEN 1 ELSE 0 END) AS organic_count,
    SUM(CASE WHEN sr.type = 'AI_REFERENCE' THEN 1 ELSE 0 END) AS ai_ref_count
FROM perxcept_extension.search_results sr
JOIN perxcept_extension.user_speciality_mappings usm ON sr.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = sr.id
    AND ga.entity_type = IF(sr.type = 'SPONSORED_AD', 'SEARCH_AD', 'SEARCH_RESULT')
JOIN perxcept_extension.gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN perxcept_extension.brand_terms bt ON gab.brand_id = bt.id
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
GROUP BY bt.standard_name
ORDER BY paid_count DESC
LIMIT 50;
```

## Disease-Related Search Results
```sql
SELECT dt.standard_name AS disease, COUNT(DISTINCT sr.id) AS result_count
FROM perxcept_extension.search_results sr
JOIN perxcept_extension.user_speciality_mappings usm ON sr.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = sr.id
    AND ga.entity_type = IF(sr.type = 'SPONSORED_AD', 'SEARCH_AD', 'SEARCH_RESULT')
LEFT JOIN perxcept_extension.gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN perxcept_extension.disease_terms dt ON gad.disease_id = dt.id
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND dt.standard_name IS NOT NULL
GROUP BY dt.standard_name
ORDER BY result_count DESC
LIMIT 50;
```

## Monthly Search Volume Trend
```sql
SELECT DATE_FORMAT(sr.created, '%Y-%m') AS month,
       sr.type,
       COUNT(DISTINCT sr.id) AS result_count
FROM perxcept_extension.search_results sr
JOIN perxcept_extension.user_speciality_mappings usm ON sr.user_id = usm.user_id
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY month, sr.type
ORDER BY month, sr.type
LIMIT 50;
```
