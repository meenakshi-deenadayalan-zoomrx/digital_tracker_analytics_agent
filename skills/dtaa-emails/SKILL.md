---
name: "DTAA Emails Channel"
description: "Emails channel exploratory analysis — counts, sender breakdowns, subject analysis, annotation summaries. Activate for non-metric email questions. For SOV/Reach/Frequency use /dtaa-emails-metrics instead."
---

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
FROM emails e
JOIN user_speciality_mappings usm ON e.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = e.id AND ga.entity_type = 'EMAIL'
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
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
```

## Common Query Patterns

### Total email count by date range
```sql
SELECT COUNT(DISTINCT e.id) AS total_emails, COUNT(DISTINCT e.user_id) AS unique_users
FROM emails e
JOIN user_speciality_mappings usm ON e.user_id = usm.user_id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30);
```

### Emails by brand
```sql
SELECT bt.standard_name AS brand, COUNT(DISTINCT e.id) AS email_count
FROM emails e
JOIN user_speciality_mappings usm ON e.user_id = usm.user_id
JOIN gpt_annotations ga ON ga.entity_id = e.id AND ga.entity_type = 'EMAIL'
JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN brand_terms bt ON gab.brand_id = bt.id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
  AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
GROUP BY bt.standard_name
ORDER BY email_count DESC;
```

### Emails by sender category
```sql
SELECT e.sender_category, COUNT(DISTINCT e.id) AS email_count
FROM emails e
JOIN user_speciality_mappings usm ON e.user_id = usm.user_id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY e.sender_category
ORDER BY email_count DESC;
```

### Emails with embedded ads
```sql
SELECT e.ad_embedded_email, COUNT(DISTINCT e.id) AS email_count
FROM emails e
JOIN user_speciality_mappings usm ON e.user_id = usm.user_id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY e.ad_embedded_email;
```

### Top senders
```sql
SELECT e.sender, e.sender_email, COUNT(DISTINCT e.id) AS email_count
FROM emails e
JOIN user_speciality_mappings usm ON e.user_id = usm.user_id
WHERE e.received_date BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
  AND usm.speciality_id NOT IN (28, 30)
GROUP BY e.sender, e.sender_email
ORDER BY email_count DESC
LIMIT 20;
```

## References
- Full schema: `dtaa/references/schema.md`
- SQL guidelines: `dtaa/references/guidelines.md`
- Common patterns: `references/query_patterns.md`
