# Search Channel — Additional Query Patterns

## Search Queries with AI Responses
```sql
SELECT sq.id, sq.search_query, ar.response_type, ar.llm_annotation_status
FROM search_queries sq
JOIN user_speciality_mappings usm ON sq.user_id = usm.user_id
LEFT JOIN ai_responses ar ON ar.search_query_id = sq.id
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
FROM search_results sr
JOIN user_speciality_mappings usm ON sr.user_id = usm.user_id
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND sr.type = '{type}'
GROUP BY sr.rank
ORDER BY sr.rank;
```

## Brand Presence in Organic vs Paid Search
```sql
SELECT
    bt.standard_name AS brand,
    SUM(CASE WHEN sr.type = 'SPONSORED_AD' THEN 1 ELSE 0 END) AS paid_count,
    SUM(CASE WHEN sr.type = 'ORGANIC' THEN 1 ELSE 0 END) AS organic_count,
    SUM(CASE WHEN sr.type = 'AI_REFERENCE' THEN 1 ELSE 0 END) AS ai_ref_count
FROM search_results sr
JOIN user_speciality_mappings usm ON sr.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = sr.id
    AND ga.entity_type = IF(sr.type = 'SPONSORED_AD', 'SEARCH_AD', 'SEARCH_RESULT')
JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN brand_terms bt ON gab.brand_id = bt.id
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
GROUP BY bt.standard_name
ORDER BY paid_count DESC;
```

## Disease-Related Search Results
```sql
SELECT dt.standard_name AS disease, COUNT(DISTINCT sr.id) AS result_count
FROM search_results sr
JOIN user_speciality_mappings usm ON sr.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = sr.id
    AND ga.entity_type = IF(sr.type = 'SPONSORED_AD', 'SEARCH_AD', 'SEARCH_RESULT')
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN disease_terms dt ON gad.disease_id = dt.id
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND dt.standard_name IS NOT NULL
GROUP BY dt.standard_name
ORDER BY result_count DESC;
```

## Monthly Search Volume Trend
```sql
SELECT DATE_FORMAT(sr.created, '%Y-%m') AS month,
       sr.type,
       COUNT(DISTINCT sr.id) AS result_count
FROM search_results sr
JOIN user_speciality_mappings usm ON sr.user_id = usm.user_id
WHERE sr.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY month, sr.type
ORDER BY month, sr.type;
```
