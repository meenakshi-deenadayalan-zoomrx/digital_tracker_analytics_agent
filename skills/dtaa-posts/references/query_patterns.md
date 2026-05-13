# Posts Channel — Additional Query Patterns

## Posts by Disease
```sql
SELECT dt.standard_name AS disease, COUNT(DISTINCT p.id) AS post_count
FROM posts p
JOIN web_content_posts wcp ON wcp.post_id = p.id
JOIN web_contents wc ON wcp.web_content_id = wc.id
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = p.id AND ga.entity_type = 'POST'
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN disease_terms dt ON gad.disease_id = dt.id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND dt.standard_name IS NOT NULL
GROUP BY dt.standard_name
ORDER BY post_count DESC;
```

## Posts by Manufacturer
```sql
SELECT mt.standard_name AS manufacturer, COUNT(DISTINCT p.id) AS post_count
FROM posts p
JOIN web_content_posts wcp ON wcp.post_id = p.id
JOIN web_contents wc ON wcp.web_content_id = wc.id
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = p.id AND ga.entity_type = 'POST'
JOIN gpt_annotations_manufacturers gam ON ga.id = gam.gpt_annotation_id
JOIN manufacturer_terms mt ON gam.manufacturer_id = mt.id
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY mt.standard_name
ORDER BY post_count DESC;
```

## Posts with Media
```sql
SELECT p.id, p.account_name, m.source_url
FROM posts p
JOIN web_content_posts wcp ON wcp.post_id = p.id
JOIN web_contents wc ON wcp.web_content_id = wc.id
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
LEFT JOIN media m ON m.entity_id = p.id AND m.entity_type = 'POST'
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
FROM posts p
JOIN web_content_posts wcp ON wcp.post_id = p.id
JOIN web_contents wc ON wcp.web_content_id = wc.id
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = p.id AND ga.entity_type = 'POST'
WHERE wc.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30);
```
