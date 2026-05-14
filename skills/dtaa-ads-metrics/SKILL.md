---
name: "DTAA Ads Metrics"
description: "Ads channel metrics: Share of Voice (SOV), Reach, and Frequency. Activate when user asks for brand SOV, reach, or frequency specifically for the ads channel."
---

# DTAA — Ads Channel Metrics (SOV, Reach, Frequency)

## Metrics Supported
- **Share of Voice (SOV)**: Brand's average share of ad exposures per target user, relative to all queried brands
- **Reach**: Count of distinct target users exposed to a brand's ads
- **Frequency**: Average ad exposures per **reached** user (not per total universe)

## Channel Adaptation (from base template)

| Placeholder | Ads Value |
|-------------|-----------|
| `{channel_table}` | `ads ct` |
| `{date_column}` | `ct.created` |
| `{ga_join_condition}` | `ga.entity_id = ct.id AND ga.entity_type = 'AD'` |
| `{annotation_join}` | *(none — direct join)* |
| `user_wave_id filter` | `AND ct.user_wave_id IS NULL` |

## Standard SOV Query (1D — by brand)

> **Note**: `dtsa_mysql_read` rejects CTEs (`WITH`). This query uses nested subqueries directly.
> See `dtaa/references/sov_base_template.md` for the CTE reference version.

```sql
-- Ads SOV — no-CTE, ready for dtsa_mysql_read
-- Frequency = total brand exposures / distinct reached users (not universe)
SELECT
    brand_name,
    ROUND(AVG(individual_sov) * 100, 2)                                                       AS sov_percentage,
    SUM(CASE WHEN brand_items > 0 THEN 1 ELSE 0 END)                                         AS reach,
    SUM(brand_items)                                                                           AS total_brand_exposures,
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
            FROM ads ct
            JOIN users u ON ct.user_id = u.id
            JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN user_speciality_mappings usm ON ct.user_id = usm.user_id
            JOIN gpt_annotations ga ON ga.entity_id = ct.id AND ga.entity_type = 'AD'
            JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE ct.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND ct.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY ct.id) cn) au
    CROSS JOIN (SELECT DISTINCT brand_name FROM (
            SELECT DISTINCT ct.id AS item_id, ct.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM ads ct
            JOIN users u ON ct.user_id = u.id
            JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN user_speciality_mappings usm ON ct.user_id = usm.user_id
            JOIN gpt_annotations ga ON ga.entity_id = ct.id AND ga.entity_type = 'AD'
            JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE ct.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND ct.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY ct.id) cn) tb
    LEFT JOIN (SELECT user_id, brand_name, COUNT(DISTINCT item_id) AS brand_items FROM (
            SELECT DISTINCT ct.id AS item_id, ct.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM ads ct
            JOIN users u ON ct.user_id = u.id
            JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN user_speciality_mappings usm ON ct.user_id = usm.user_id
            JOIN gpt_annotations ga ON ga.entity_id = ct.id AND ga.entity_type = 'AD'
            JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE ct.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND ct.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY ct.id) cn GROUP BY user_id, brand_name) uba
        ON au.user_id = uba.user_id AND tb.brand_name = uba.brand_name
    LEFT JOIN (SELECT user_id, COUNT(DISTINCT item_id) AS total_items FROM (
            SELECT DISTINCT ct.id AS item_id, ct.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM ads ct
            JOIN users u ON ct.user_id = u.id
            JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN user_speciality_mappings usm ON ct.user_id = usm.user_id
            JOIN gpt_annotations ga ON ga.entity_id = ct.id AND ga.entity_type = 'AD'
            JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE ct.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND ct.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY ct.id) cn GROUP BY user_id) uta
        ON au.user_id = uta.user_id
) user_brand_sov
GROUP BY brand_name
ORDER BY sov_percentage DESC;
```

## 2D SOV (Brand × Website)

> **⚠️ `uta` denominator rule**: In 2D queries, the `uta` subquery must group by `user_id` ONLY — **never** by the second dimension. The denominator is the user's total items across all dimensions. Including the dimension in `uta`'s GROUP BY breaks SOV (each cell divides by items-within-that-dimension rather than total items, making percentages non-comparable).

Add `dimension` to the inner `cn` subquery and carry through the CROSS JOIN:
```sql
-- In inner cn subquery SELECT and GROUP BY:
LEFT JOIN web_contents wc ON ct.web_content_id = wc.id
LEFT JOIN tracked_urls turl ON wc.tracked_url_id = turl.id
-- Add: COALESCE(turl.url, 'Non-HC') AS dimension
-- GROUP BY ct.id, dimension

-- In CROSS JOIN tb: SELECT DISTINCT brand_name, dimension FROM (cn)
-- In uba LEFT JOIN: GROUP BY user_id, brand_name, dimension; add dimension to ON condition
-- In uta LEFT JOIN: GROUP BY user_id ONLY (no dimension)
-- In outer SELECT and GROUP BY: add dimension column
```

## Disease Filter Patterns (Normal Mode)

```sql
-- With disease filter (default):
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN disease_terms dt ON gad.disease_id = dt.id
-- WHERE: AND LOWER(dt.standard_name) REGEXP '{disease_regex}'

-- With TA agnostic included:
-- WHERE: AND (LOWER(dt.standard_name) REGEXP '{disease_regex}' OR dt.standard_name IS NULL)

-- Without disease filter:
-- Remove disease joins and WHERE conditions
```

## Project Mode Adaptations

In Project Mode, filters come from `report_filters_*` tables — not from user-provided text. Replace the patterns above with the ID-based versions below.

### Brand Filter
```sql
-- Replace: AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
-- With:    AND gab.brand_id IN ({brand_ids})
-- No brand_normalization CASE needed — use GROUP_CONCAT(DISTINCT bt.standard_name) directly
```

### Disease / Indication Filter
```sql
-- Replace the disease_terms REGEXP join with:
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
-- Then apply the appropriate filter from report_filters_indications_diseases:
-- disease-level only:   AND gad.disease_id IN ({disease_only_ids})
-- indication-specific:  AND gad.indication_id IN ({specific_indication_ids})
-- mixed:                AND (gad.disease_id IN ({disease_only_ids}) OR gad.indication_id IN ({specific_indication_ids}))
```

### QC Override — Brands
Replace `JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id`:
```sql
JOIN (
    SELECT gab.gpt_annotation_id,
           COALESCE(rqb.brand_id, gab.brand_id) AS brand_id
    FROM gpt_annotations_brands gab
    LEFT JOIN report_qc_brands rqb
        ON rqb.gpt_annotations_id = gab.gpt_annotation_id
        AND rqb.project_id = {project_id}
) gab ON ga.id = gab.gpt_annotation_id
JOIN brand_terms bt ON gab.brand_id = bt.id
```

### QC Override — Disease / Indication
Replace `LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id`:
```sql
LEFT JOIN (
    SELECT gad.gpt_annotation_id,
           COALESCE(rqid.disease_id, gad.disease_id)       AS disease_id,
           COALESCE(rqid.indication_id, gad.indication_id) AS indication_id
    FROM gpt_annotations_diseases gad
    LEFT JOIN report_qc_indications_diseases rqid
        ON rqid.gpt_annotations_id = gad.gpt_annotation_id
        AND rqid.project_id = {project_id}
) gad ON ga.id = gad.gpt_annotation_id
```

Full SQL reference: `dtaa/references/project_mode.md`

## Required Parameters

**Normal Mode**:
- `project_id` — from `projects` table (confirm via HitL)
- `start_date`, `end_date` — in 'YYYY-MM-DD' format
- `brands` — list confirmed via HitL discovery
- `diseases` (optional) — confirmed via HitL
- `should_include_null_diseases` — confirmed with user (default: NO)

**Project Mode** (passed by orchestrator after loading report_filters):
- `project_id` — resolved from project name
- `start_date`, `end_date` — provided by user
- `brand_ids` — from `report_filters_brands`
- `disease_only_ids` — disease_ids where indication_id IS NULL in `report_filters_indications_diseases`
- `specific_indication_ids` — indication_ids where indication_id IS NOT NULL

## References
- Base template (CTE + no-CTE reference): `dtaa/references/sov_base_template.md`
- Project Mode SQL patterns: `dtaa/references/project_mode.md`
- Schema: `dtaa/references/schema.md`
- Guidelines: `dtaa/references/guidelines.md`
