---
name: "DTAA Ads Channel"
description: "Ads channel exploratory analysis — counts, breakdowns, filters, annotation summaries. Activate for non-metric ads questions. For SOV/Reach/Frequency use /dtaa-ads-metrics instead."
---

# DTAA — Ads Channel (Exploratory)

## Channel Overview
- **Primary table**: `ads`
- **Annotation entity type**: `AD`
- **Date column**: `created`
- **Mandatory filters**: `user_wave_id IS NULL`, speciality exclusion (IDs 28, 30)

## Table Schema (Key Columns)
```
ads: id, url, web_content_id (NULL=non-healthcare source), created,
     user_id, client_id, redirect_url, destination_url,
     type (STATIC/DYNAMIC/SCREENSHOT/CANVAS/EMAIL),
     is_valuable, llm_annotation_status, user_wave_id
```

## Standard Join Pattern
```sql
FROM ads a
JOIN user_speciality_mappings usm ON a.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = a.id AND ga.entity_type = 'AD'
WHERE a.user_wave_id IS NULL
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

-- Add manufacturers:
JOIN gpt_annotations_manufacturers gam ON ga.id = gam.gpt_annotation_id
JOIN manufacturer_terms mt ON gam.manufacturer_id = mt.id
```

## Ads ↔ Web Contents Relationship
```sql
-- Where was the ad captured? (NULL = non-healthcare site)
LEFT JOIN web_contents wc ON a.web_content_id = wc.id
LEFT JOIN tracked_urls tu ON wc.tracked_url_id = tu.id
```

## Common Query Patterns

### Total ad count by date range
```sql
SELECT COUNT(DISTINCT a.id) AS total_ads
FROM ads a
JOIN user_speciality_mappings usm ON a.user_id = usm.user_id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30);
```

### Ads by brand
```sql
SELECT bt.standard_name AS brand, COUNT(DISTINCT a.id) AS ad_count
FROM ads a
JOIN user_speciality_mappings usm ON a.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = a.id AND ga.entity_type = 'AD'
JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN brand_terms bt ON gab.brand_id = bt.id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
GROUP BY bt.standard_name
ORDER BY ad_count DESC;
```

### Unique users who saw ads (reach without SOV)
```sql
SELECT COUNT(DISTINCT a.user_id) AS unique_users
FROM ads a
JOIN user_speciality_mappings usm ON a.user_id = usm.user_id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30);
```

### Ads by source website
```sql
SELECT tu.url AS website, COUNT(DISTINCT a.id) AS ad_count
FROM ads a
JOIN user_speciality_mappings usm ON a.user_id = usm.user_id
LEFT JOIN web_contents wc ON a.web_content_id = wc.id
LEFT JOIN tracked_urls tu ON wc.tracked_url_id = tu.id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY tu.url
ORDER BY ad_count DESC;
```

## References
- Full schema: `dtaa/references/schema.md`
- SQL guidelines: `dtaa/references/guidelines.md`
- Common patterns: `references/query_patterns.md`
