# Ads Channel — Additional Query Patterns

## Ads by Type (STATIC/DYNAMIC/SCREENSHOT/CANVAS/EMAIL)
```sql
SELECT a.type, COUNT(DISTINCT a.id) AS count
FROM ads a
JOIN user_speciality_mappings usm ON a.user_id = usm.user_id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY a.type
ORDER BY count DESC;
```

## Ads by Manufacturer
```sql
SELECT mt.standard_name AS manufacturer, COUNT(DISTINCT a.id) AS ad_count
FROM ads a
JOIN user_speciality_mappings usm ON a.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = a.id AND ga.entity_type = 'AD'
JOIN gpt_annotations_manufacturers gam ON ga.id = gam.gpt_annotation_id
JOIN manufacturer_terms mt ON gam.manufacturer_id = mt.id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY mt.standard_name
ORDER BY ad_count DESC;
```

## Healthcare vs Non-Healthcare Ads
```sql
SELECT
    SUM(CASE WHEN ga.is_healthcare_relevant = 1 THEN 1 ELSE 0 END) AS healthcare_ads,
    SUM(CASE WHEN ga.is_healthcare_relevant = 0 THEN 1 ELSE 0 END) AS non_healthcare_ads,
    COUNT(*) AS total_ads
FROM ads a
JOIN user_speciality_mappings usm ON a.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = a.id AND ga.entity_type = 'AD'
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30);
```

## Ads by Target Audience (HCP vs Patient)
```sql
SELECT ga.target_audience, COUNT(DISTINCT a.id) AS ad_count
FROM ads a
JOIN user_speciality_mappings usm ON a.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = a.id AND ga.entity_type = 'AD'
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY ga.target_audience;
```

## Ads by Disease
```sql
SELECT dt.standard_name AS disease, COUNT(DISTINCT a.id) AS ad_count
FROM ads a
JOIN user_speciality_mappings usm ON a.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = a.id AND ga.entity_type = 'AD'
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN disease_terms dt ON gad.disease_id = dt.id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND dt.standard_name IS NOT NULL  -- exclude TA agnostic unless requested
GROUP BY dt.standard_name
ORDER BY ad_count DESC;
```

## Monthly Trend of Ads
```sql
SELECT DATE_FORMAT(a.created, '%Y-%m') AS month, COUNT(DISTINCT a.id) AS ad_count
FROM ads a
JOIN user_speciality_mappings usm ON a.user_id = usm.user_id
WHERE a.created BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND a.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY month
ORDER BY month;
```
