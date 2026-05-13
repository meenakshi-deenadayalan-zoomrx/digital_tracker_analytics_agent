# Web Contents Channel — Additional Query Patterns

## Visits by Disease
```sql
SELECT dt.standard_name AS disease, COUNT(DISTINCT wc.id) AS visit_count
FROM web_contents wc
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN web_content_groups wcg ON wc.web_content_group_id = wcg.id
JOIN gpt_annotations ga ON ga.entity_id = wcg.id AND ga.entity_type = 'WEB_CONTENT_GROUP'
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN disease_terms dt ON gad.disease_id = dt.id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND dt.standard_name IS NOT NULL  -- exclude TA agnostic unless requested
GROUP BY dt.standard_name
ORDER BY visit_count DESC;
```

## Visits by Target Audience (HCP vs Patient)
```sql
SELECT ga.target_audience, COUNT(DISTINCT wc.id) AS visit_count,
       COUNT(DISTINCT wc.user_id) AS unique_users
FROM web_contents wc
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN web_content_groups wcg ON wc.web_content_group_id = wcg.id
JOIN gpt_annotations ga ON ga.entity_id = wcg.id AND ga.entity_type = 'WEB_CONTENT_GROUP'
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY ga.target_audience;
```

## Monthly Visit Trend
```sql
SELECT DATE_FORMAT(wc.created, '%Y-%m') AS month,
       COUNT(DISTINCT wc.id) AS visit_count,
       COUNT(DISTINCT wc.user_id) AS unique_users
FROM web_contents wc
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY month
ORDER BY month;
```

## Website URL Category Breakdown
```sql
SELECT tu.category, COUNT(DISTINCT wc.id) AS visit_count
FROM web_contents wc
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
LEFT JOIN tracked_urls tu ON wc.tracked_url_id = tu.id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY tu.category
ORDER BY visit_count DESC;
```

## Topic Breakdown
```sql
SELECT gat.primary_topic, COUNT(DISTINCT wc.id) AS visit_count
FROM web_contents wc
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN web_content_groups wcg ON wc.web_content_group_id = wcg.id
JOIN gpt_annotations ga ON ga.entity_id = wcg.id AND ga.entity_type = 'WEB_CONTENT_GROUP'
JOIN gpt_annotations_topics gat ON ga.id = gat.gpt_annotation_id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY gat.primary_topic
ORDER BY visit_count DESC;
```
