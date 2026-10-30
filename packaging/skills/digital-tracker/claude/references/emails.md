
# DTAA — Emails Channel (Exploratory)

## Channel Overview
- **Primary table**: `emails`
- **Annotation entity type**: `EMAIL`
- **Date column**: `received_date` (ALWAYS use this — NOT `created`)
- **Mandatory filters**: User quality filter (speciality_id NOT IN 28, 30)
- **Note**: `emails` table does NOT have `user_wave_id` — no survey filter needed here

## Table Schema (Key Columns)
```
emails: id, web_content_id (FK→web_contents.id), subject, sender, sender_email,
        received_date (DATETIME — USE THIS FOR DATE FILTERS),
        created, user_id, client_id,
        sender_category (MEDICAL_REPRESENTATIVE/MANUFACTURER/THIRD_PARTY_WEBSITE),
        ad_embedded_email (UNKNOWN/YES/NO)
```

## Standard Join Pattern
```sql
FROM perxcept_extension.emails e
JOIN perxcept_extension.user_speciality_mappings usm ON e.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = e.id AND ga.entity_type = 'EMAIL'
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
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
```

## Common Query Patterns

### Total email count by date range
```sql
SELECT COUNT(DISTINCT e.id) AS total_emails, COUNT(DISTINCT e.user_id) AS unique_users
FROM perxcept_extension.emails e
JOIN perxcept_extension.user_speciality_mappings usm ON e.user_id = usm.user_id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
LIMIT 50;
```

### Emails by brand
```sql
SELECT bt.standard_name AS brand, COUNT(DISTINCT e.id) AS email_count
FROM perxcept_extension.emails e
JOIN perxcept_extension.user_speciality_mappings usm ON e.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = e.id AND ga.entity_type = 'EMAIL'
JOIN perxcept_extension.gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN perxcept_extension.brand_terms bt ON gab.brand_id = bt.id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
GROUP BY bt.standard_name
ORDER BY email_count DESC
LIMIT 50;
```

### Emails by sender category
```sql
SELECT e.sender_category, COUNT(DISTINCT e.id) AS email_count
FROM perxcept_extension.emails e
JOIN perxcept_extension.user_speciality_mappings usm ON e.user_id = usm.user_id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY e.sender_category
ORDER BY email_count DESC
LIMIT 50;
```

### Emails with embedded ads
```sql
SELECT e.ad_embedded_email, COUNT(DISTINCT e.id) AS email_count
FROM perxcept_extension.emails e
JOIN perxcept_extension.user_speciality_mappings usm ON e.user_id = usm.user_id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY e.ad_embedded_email
LIMIT 50;
```

### Top senders
```sql
SELECT e.sender, e.sender_email, COUNT(DISTINCT e.id) AS email_count
FROM perxcept_extension.emails e
JOIN perxcept_extension.user_speciality_mappings usm ON e.user_id = usm.user_id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY e.sender, e.sender_email
ORDER BY email_count DESC
LIMIT 20;
```

## References
- Full schema: `references/schema.md`
- SQL guidelines: `references/guidelines.md`

## Extended Query Patterns

# Emails Channel — Additional Query Patterns

## Emails by Disease
```sql
SELECT dt.standard_name AS disease, COUNT(DISTINCT e.id) AS email_count
FROM perxcept_extension.emails e
JOIN perxcept_extension.user_speciality_mappings usm ON e.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = e.id AND ga.entity_type = 'EMAIL'
LEFT JOIN perxcept_extension.gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN perxcept_extension.disease_terms dt ON gad.disease_id = dt.id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND dt.standard_name IS NOT NULL  -- exclude TA agnostic unless requested
GROUP BY dt.standard_name
ORDER BY email_count DESC
LIMIT 50;
```

## Monthly Email Trend
```sql
SELECT DATE_FORMAT(e.received_date, '%Y-%m') AS month, COUNT(DISTINCT e.id) AS email_count
FROM perxcept_extension.emails e
JOIN perxcept_extension.user_speciality_mappings usm ON e.user_id = usm.user_id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY month
ORDER BY month
LIMIT 50;
```

## Emails by Manufacturer
```sql
SELECT mt.standard_name AS manufacturer, COUNT(DISTINCT e.id) AS email_count
FROM perxcept_extension.emails e
JOIN perxcept_extension.user_speciality_mappings usm ON e.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = e.id AND ga.entity_type = 'EMAIL'
JOIN perxcept_extension.gpt_annotations_manufacturers gam ON ga.id = gam.gpt_annotation_id
JOIN perxcept_extension.manufacturer_terms mt ON gam.manufacturer_id = mt.id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY mt.standard_name
ORDER BY email_count DESC
LIMIT 50;
```

## Healthcare vs Non-Healthcare Emails
```sql
SELECT
    SUM(CASE WHEN ga.is_healthcare_relevant = 1 THEN 1 ELSE 0 END) AS healthcare_emails,
    SUM(CASE WHEN ga.is_healthcare_relevant = 0 THEN 1 ELSE 0 END) AS non_healthcare_emails,
    COUNT(*) AS total_emails
FROM perxcept_extension.emails e
JOIN perxcept_extension.user_speciality_mappings usm ON e.user_id = usm.user_id
JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = e.id AND ga.entity_type = 'EMAIL'
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
LIMIT 50;
```
