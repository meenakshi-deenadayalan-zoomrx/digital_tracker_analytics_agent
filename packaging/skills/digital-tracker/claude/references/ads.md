
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
FROM perxcept_extension.ads a
JOIN perxcept_extension.user_speciality_mappings usm ON a.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = a.id AND ga.entity_type = 'AD'
WHERE a.user_wave_id IS NULL
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

-- Add manufacturers:
JOIN perxcept_extension.gpt_annotations_manufacturers gam ON ga.id = gam.gpt_annotation_id
JOIN perxcept_extension.manufacturer_terms mt ON gam.manufacturer_id = mt.id
```

## Ads ↔ Web Contents Relationship
```sql
-- Where was the ad captured? (NULL = non-healthcare site)
LEFT JOIN perxcept_extension.web_contents wc ON a.web_content_id = wc.id
LEFT JOIN perxcept_extension.tracked_urls tu ON wc.tracked_url_id = tu.id
```

## Common Query Patterns

### Total ad count by date range
```sql
SELECT COUNT(DISTINCT a.id) AS total_ads
FROM perxcept_extension.ads a
JOIN perxcept_extension.user_speciality_mappings usm ON a.user_id = usm.user_id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
LIMIT 50;
```

### Ads by brand
```sql
SELECT bt.standard_name AS brand, COUNT(DISTINCT a.id) AS ad_count
FROM perxcept_extension.ads a
JOIN perxcept_extension.user_speciality_mappings usm ON a.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = a.id AND ga.entity_type = 'AD'
JOIN perxcept_extension.gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN perxcept_extension.brand_terms bt ON gab.brand_id = bt.id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
GROUP BY bt.standard_name
ORDER BY ad_count DESC
LIMIT 50;
```

### Unique users who saw ads (reach without SOV)
```sql
SELECT COUNT(DISTINCT a.user_id) AS unique_users
FROM perxcept_extension.ads a
JOIN perxcept_extension.user_speciality_mappings usm ON a.user_id = usm.user_id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
LIMIT 50;
```

### Ads by source website
```sql
SELECT tu.url AS website, COUNT(DISTINCT a.id) AS ad_count
FROM perxcept_extension.ads a
JOIN perxcept_extension.user_speciality_mappings usm ON a.user_id = usm.user_id
LEFT JOIN perxcept_extension.web_contents wc ON a.web_content_id = wc.id
LEFT JOIN perxcept_extension.tracked_urls tu ON wc.tracked_url_id = tu.id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY tu.url
ORDER BY ad_count DESC
LIMIT 50;
```

## References
- Full schema: `references/schema.md`
- SQL guidelines: `references/guidelines.md`

## Extended Query Patterns

# Ads Channel — Additional Query Patterns

## Ads by Type (STATIC/DYNAMIC/SCREENSHOT/CANVAS/EMAIL)
```sql
SELECT a.type, COUNT(DISTINCT a.id) AS count
FROM perxcept_extension.ads a
JOIN perxcept_extension.user_speciality_mappings usm ON a.user_id = usm.user_id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY a.type
ORDER BY count DESC
LIMIT 50;
```

## Ads by Manufacturer
```sql
SELECT mt.standard_name AS manufacturer, COUNT(DISTINCT a.id) AS ad_count
FROM perxcept_extension.ads a
JOIN perxcept_extension.user_speciality_mappings usm ON a.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = a.id AND ga.entity_type = 'AD'
JOIN perxcept_extension.gpt_annotations_manufacturers gam ON ga.id = gam.gpt_annotation_id
JOIN perxcept_extension.manufacturer_terms mt ON gam.manufacturer_id = mt.id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY mt.standard_name
ORDER BY ad_count DESC
LIMIT 50;
```

## Healthcare vs Non-Healthcare Ads
```sql
SELECT
    SUM(CASE WHEN ga.is_healthcare_relevant = 1 THEN 1 ELSE 0 END) AS healthcare_ads,
    SUM(CASE WHEN ga.is_healthcare_relevant = 0 THEN 1 ELSE 0 END) AS non_healthcare_ads,
    COUNT(*) AS total_ads
FROM perxcept_extension.ads a
JOIN perxcept_extension.user_speciality_mappings usm ON a.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = a.id AND ga.entity_type = 'AD'
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
LIMIT 50;
```

## Ads by Target Audience (HCP vs Patient)
```sql
SELECT ga.target_audience, COUNT(DISTINCT a.id) AS ad_count
FROM perxcept_extension.ads a
JOIN perxcept_extension.user_speciality_mappings usm ON a.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = a.id AND ga.entity_type = 'AD'
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY ga.target_audience
LIMIT 50;
```

## Ads by Disease
```sql
SELECT dt.standard_name AS disease, COUNT(DISTINCT a.id) AS ad_count
FROM perxcept_extension.ads a
JOIN perxcept_extension.user_speciality_mappings usm ON a.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = a.id AND ga.entity_type = 'AD'
LEFT JOIN perxcept_extension.gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN perxcept_extension.disease_terms dt ON gad.disease_id = dt.id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND dt.standard_name IS NOT NULL  -- exclude TA agnostic unless requested
GROUP BY dt.standard_name
ORDER BY ad_count DESC
LIMIT 50;
```

## Monthly Trend of Ads
```sql
SELECT DATE_FORMAT(a.created, '%Y-%m') AS month, COUNT(DISTINCT a.id) AS ad_count
FROM perxcept_extension.ads a
JOIN perxcept_extension.user_speciality_mappings usm ON a.user_id = usm.user_id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY month
ORDER BY month
LIMIT 50;
```
