# Emails Channel — Additional Query Patterns

## Emails by Disease
```sql
SELECT dt.standard_name AS disease, COUNT(DISTINCT e.id) AS email_count
FROM emails e
JOIN user_speciality_mappings usm ON e.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = e.id AND ga.entity_type = 'EMAIL'
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN disease_terms dt ON gad.disease_id = dt.id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND dt.standard_name IS NOT NULL  -- exclude TA agnostic unless requested
GROUP BY dt.standard_name
ORDER BY email_count DESC;
```

## Monthly Email Trend
```sql
SELECT DATE_FORMAT(e.received_date, '%Y-%m') AS month, COUNT(DISTINCT e.id) AS email_count
FROM emails e
JOIN user_speciality_mappings usm ON e.user_id = usm.user_id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY month
ORDER BY month;
```

## Emails by Manufacturer
```sql
SELECT mt.standard_name AS manufacturer, COUNT(DISTINCT e.id) AS email_count
FROM emails e
JOIN user_speciality_mappings usm ON e.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = e.id AND ga.entity_type = 'EMAIL'
JOIN gpt_annotations_manufacturers gam ON ga.id = gam.gpt_annotation_id
JOIN manufacturer_terms mt ON gam.manufacturer_id = mt.id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY mt.standard_name
ORDER BY email_count DESC;
```

## Healthcare vs Non-Healthcare Emails
```sql
SELECT
    SUM(CASE WHEN ga.is_healthcare_relevant = 1 THEN 1 ELSE 0 END) AS healthcare_emails,
    SUM(CASE WHEN ga.is_healthcare_relevant = 0 THEN 1 ELSE 0 END) AS non_healthcare_emails,
    COUNT(*) AS total_emails
FROM emails e
JOIN user_speciality_mappings usm ON e.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = e.id AND ga.entity_type = 'EMAIL'
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30);
```
