---
name: "DTAA Emails Metrics"
description: "Emails channel metrics: Share of Voice (SOV), Reach, and Frequency. Activate when user asks for brand SOV, reach, or frequency specifically for the emails channel."
---

# DTAA — Emails Channel Metrics (SOV, Reach, Frequency)

## Metrics Supported
- **Share of Voice (SOV)**: Brand's average share of emails received per target user, relative to all queried brands
- **Reach**: Count of distinct target users who received a brand's emails
- **Frequency**: Average emails received per **reached** user (not per total universe)

## Key Differences from Other Channels
- Date column: `received_date` (NOT `created`)
- No `user_wave_id` filter — `emails` table has no `user_wave_id` column
- `entity_type = 'EMAIL'`

## Channel Adaptation (from base template)

| Placeholder | Emails Value |
|-------------|-------------|
| `{channel_table}` | `emails ct` |
| `{date_column}` | `ct.received_date` |
| `{ga_join_condition}` | `ga.entity_id = ct.id AND ga.entity_type = 'EMAIL'` |
| `{annotation_join}` | *(none — direct join)* |
| `user_wave_id filter` | *(not applicable — no user_wave_id in emails)* |

## Standard SOV Query (1D — by brand)

> **Note**: `dtsa_mysql_read` rejects CTEs (`WITH`). This query uses nested subqueries directly.
> See `dtaa/references/sov_base_template.md` for the CTE reference version.

```sql
-- Emails SOV — no-CTE, ready for dtsa_mysql_read
-- Frequency = total brand emails / distinct reached users (not universe)
SELECT
    brand_name,
    ROUND(AVG(individual_sov) * 100, 2)                                                       AS sov_percentage,
    SUM(CASE WHEN brand_items > 0 THEN 1 ELSE 0 END)                                         AS reach,
    SUM(brand_items)                                                                           AS total_brand_emails,
    ROUND(SUM(brand_items) / NULLIF(SUM(CASE WHEN brand_items > 0 THEN 1 ELSE 0 END), 0), 2) AS frequency
FROM (
    SELECT
        au.user_id,
        tb.brand_name,
        COALESCE(uba.brand_items, 0)                    AS brand_items,
        COALESCE(uba.brand_items / uta.total_items, 0)  AS individual_sov
    FROM (SELECT DISTINCT user_id FROM (
            SELECT DISTINCT ct.id AS item_id, ct.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM emails ct
            JOIN users u ON ct.user_id = u.id
            JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN user_speciality_mappings usm ON ct.user_id = usm.user_id
            JOIN gpt_annotations ga ON ga.entity_id = ct.id AND ga.entity_type = 'EMAIL'
            JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE ct.received_date BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY ct.id) cn) au
    CROSS JOIN (SELECT DISTINCT brand_name FROM (
            SELECT DISTINCT ct.id AS item_id, ct.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM emails ct
            JOIN users u ON ct.user_id = u.id
            JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN user_speciality_mappings usm ON ct.user_id = usm.user_id
            JOIN gpt_annotations ga ON ga.entity_id = ct.id AND ga.entity_type = 'EMAIL'
            JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE ct.received_date BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY ct.id) cn) tb
    LEFT JOIN (SELECT user_id, brand_name, COUNT(DISTINCT item_id) AS brand_items FROM (
            SELECT DISTINCT ct.id AS item_id, ct.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM emails ct
            JOIN users u ON ct.user_id = u.id
            JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN user_speciality_mappings usm ON ct.user_id = usm.user_id
            JOIN gpt_annotations ga ON ga.entity_id = ct.id AND ga.entity_type = 'EMAIL'
            JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE ct.received_date BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY ct.id) cn GROUP BY user_id, brand_name) uba
        ON au.user_id = uba.user_id AND tb.brand_name = uba.brand_name
    LEFT JOIN (SELECT user_id, COUNT(DISTINCT item_id) AS total_items FROM (
            SELECT DISTINCT ct.id AS item_id, ct.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM emails ct
            JOIN users u ON ct.user_id = u.id
            JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN user_speciality_mappings usm ON ct.user_id = usm.user_id
            JOIN gpt_annotations ga ON ga.entity_id = ct.id AND ga.entity_type = 'EMAIL'
            JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE ct.received_date BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY ct.id) cn GROUP BY user_id) uta
        ON au.user_id = uta.user_id
) user_brand_sov
GROUP BY brand_name
ORDER BY sov_percentage DESC;
```

## Disease Filter Patterns

```sql
-- With disease filter (default):
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN disease_terms dt ON gad.disease_id = dt.id
-- WHERE: AND LOWER(dt.standard_name) REGEXP '{disease_regex}'

-- With TA agnostic included:
-- WHERE: AND (LOWER(dt.standard_name) REGEXP '{disease_regex}' OR dt.standard_name IS NULL)

-- Without disease filter:
-- Remove disease joins and conditions
```

## 2D SOV (Brand × Sender Category or Month)

> **⚠️ `uta` denominator rule**: In 2D queries, the `uta` subquery must group by `user_id` ONLY — **never** by the second dimension. The denominator is the user's total emails across all dimensions. Including dimension in `uta`'s GROUP BY breaks SOV.

Sender category dimension — add to inner `cn` subquery:
```sql
ct.sender_category AS dimension
-- Add to SELECT, GROUP BY ct.id, dimension
-- In uba: GROUP BY user_id, brand_name, dimension; add dimension to ON
-- In uta: GROUP BY user_id ONLY
```

Date dimension:
```sql
DATE_FORMAT(ct.received_date, '%Y-%m') AS dimension
```

## Required Parameters
- `project_id` — from `projects` table (confirm via HitL)
- `start_date`, `end_date` — in 'YYYY-MM-DD' format
- `brands` — list confirmed via HitL discovery
- `diseases` (optional) — confirmed via HitL
- `should_include_null_diseases` — confirmed with user (default: NO)

## References
- Base template (CTE + no-CTE reference): `dtaa/references/sov_base_template.md`
- Schema: `dtaa/references/schema.md`
- Guidelines: `dtaa/references/guidelines.md`
