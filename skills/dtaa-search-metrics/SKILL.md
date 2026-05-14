---
name: "DTAA Search Metrics"
description: "Search channel metrics: Share of Voice (SOV), Reach, and Frequency for sponsored ads, organic results, and AI references. Activate when user asks for brand SOV, reach, or frequency for search results or search ads."
---

# DTAA — Search Channel Metrics (SOV, Reach, Frequency)

## Metrics Supported
- **Share of Voice (SOV)**: Brand search results as % of total search results per target user
- **Reach**: Count of distinct target users who saw a brand's search results
- **Frequency**: Average search result appearances per reached user

## Search Type Selection
Always confirm with user which type(s) of search results to analyze:
- `SPONSORED_AD` — paid search ads → entity_type: `SEARCH_AD`
- `ORGANIC` — organic search results → entity_type: `SEARCH_RESULT`
- `AI_REFERENCE` — AI response reference links → entity_type: `SEARCH_RESULT`

These can be analyzed separately or combined based on user intent.

## Key Note
- `search_results` has no `user_wave_id` — no survey filter needed on this table
- If joining `search_queries`, apply `sq.user_wave_id IS NULL`

## Channel Adaptation (from base template)

| Placeholder | Search Value |
|-------------|-------------|
| `{channel_table}` | `search_results sr` |
| `{date_column}` | `created` |
| `{ga_join_condition}` | `ga.entity_id = sr.id AND ga.entity_type = IF(sr.type = 'SPONSORED_AD', 'SEARCH_AD', 'SEARCH_RESULT')` |
| `user_wave_id filter` | *(not applicable on search_results)* |
| Type filter | `AND sr.type IN ('{types}')` |

## Standard SOV Query (1D — by brand, for a specific type)

```sql
-- CROSS JOIN ensures all active users contribute to each brand's SOV average
WITH target_users AS (
    SELECT DISTINCT u.id AS user_id
    FROM users u
    JOIN project_target_list ptl ON u.npi = ptl.npi
    JOIN user_speciality_mappings usm ON u.id = usm.user_id
    WHERE ptl.project_id = {project_id}
      AND usm.speciality_id NOT IN (28, 30)
),
search_normalized AS (
    SELECT DISTINCT
        sr.id AS item_id,
        sr.user_id,
        GROUP_CONCAT(DISTINCT
            CASE
                {brand_normalization}   -- WHEN LOWER(bt.standard_name) REGEXP '...' THEN 'Canonical Name'
                ELSE bt.standard_name
            END
        ) AS brand_name
    FROM search_results sr
    JOIN target_users tu ON sr.user_id = tu.user_id
    JOIN user_speciality_mappings usm ON sr.user_id = usm.user_id
    JOIN gpt_annotations ga ON ga.entity_id = sr.id
        AND ga.entity_type = IF(sr.type = 'SPONSORED_AD', 'SEARCH_AD', 'SEARCH_RESULT')
    JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
    JOIN brand_terms bt ON gab.brand_id = bt.id
    {disease_joins}
    WHERE sr.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
      AND usm.speciality_id NOT IN (28, 30)
      AND sr.type IN ('{search_types}')
      AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
      {disease_filter}
    GROUP BY sr.id
),
brand_sov AS (
    SELECT
        brand_name,
        AVG(individual_sov) * 100                               AS avg_user_sov,
        SUM(CASE WHEN brand_results > 0 THEN 1 ELSE 0 END)     AS reach,
        SUM(brand_results)                                      AS total_brand_results,
        SUM(brand_results) / COUNT(DISTINCT user_id)            AS frequency
    FROM (
        SELECT
            au.user_id,
            tb.brand_name,
            COALESCE(uba.brand_results, 0)                        AS brand_results,
            COALESCE(uba.brand_results / uta.total_results, 0)    AS individual_sov
        FROM (
            SELECT DISTINCT user_id FROM search_normalized
        ) au
        CROSS JOIN (
            SELECT DISTINCT brand_name FROM search_normalized
        ) tb
        LEFT JOIN (
            SELECT user_id, brand_name, COUNT(DISTINCT item_id) AS brand_results
            FROM search_normalized
            GROUP BY user_id, brand_name
        ) uba ON au.user_id = uba.user_id AND tb.brand_name = uba.brand_name
        LEFT JOIN (
            SELECT user_id, COUNT(DISTINCT item_id) AS total_results
            FROM search_normalized
            GROUP BY user_id
        ) uta ON au.user_id = uta.user_id
    ) user_brand_sov
    GROUP BY brand_name
)
SELECT
    brand_name,
    ROUND(avg_user_sov, 2)      AS sov_percentage,
    reach,
    total_brand_results,
    ROUND(frequency, 2)         AS frequency
FROM brand_sov
ORDER BY sov_percentage DESC;
```

## 2D SOV (Brand × Search Type or Engine)

Search type dimension:
```sql
-- Add to user_brand_exposures:
sr.type AS dimension
-- Apply to both CTEs; GROUP BY sr.type
```

Position/rank dimension (for sponsored ads):
```sql
-- Use rank BUCKETS — search_results.rank includes negative values (-3, -2, -1 = top-of-page placements, 1+ = numbered positions)
-- Recommended bucket expression:
CASE WHEN sr.rank = 1 THEN '1'
     WHEN sr.rank = 2 THEN '2'
     WHEN sr.rank = 3 THEN '3'
     ELSE '4+' END AS dimension
-- This maps negatives and rank 4+ into a single '4+' bucket
```

Engine dimension (requires joining search_queries):
```sql
JOIN search_queries sq ON sr.search_query_id = sq.id
-- Add sq.engine_type AS dimension
-- NOTE: search_results.search_query_id may be NULL for some periods — verify linkage
-- with SELECT COUNT(*) FROM search_results WHERE search_query_id IS NOT NULL before using
```

## Disease Filter Patterns (Normal Mode)

```sql
-- With disease filter (default):
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN disease_terms dt ON gad.disease_id = dt.id
-- WHERE: AND LOWER(dt.standard_name) REGEXP '{disease_regex}'

-- With TA agnostic included:
-- WHERE: AND (LOWER(dt.standard_name) REGEXP '{disease_regex}' OR dt.standard_name IS NULL)
```

## Project Mode Adaptations

In Project Mode, filters come from `report_filters_*` tables. Replace the patterns above with ID-based versions.

> **Note**: The SOV query above uses CTEs (`WITH`) for readability — the `dtsa_mysql_read` tool rejects CTEs. Always convert to nested subqueries before executing (see `dtaa/references/sov_base_template.md`).

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

### Search Query QC Override
When project_id is known, also apply `is_branded` overrides for search queries:
```sql
-- Replace: sq.is_branded
-- With:    COALESCE(rqsq.is_branded, sq.is_branded)
-- Add:     LEFT JOIN report_qc_search_queries rqsq ON rqsq.search_query_id = sq.id AND rqsq.project_id = {project_id}
```

Full SQL reference: `dtaa/references/project_mode.md`

## Required Parameters

**Normal Mode**:
- `project_id` — from `projects` table (confirm via HitL)
- `start_date`, `end_date` — in 'YYYY-MM-DD' format
- `brands` — list confirmed via HitL discovery
- `search_type(s)` — confirm which: SPONSORED_AD / ORGANIC / AI_REFERENCE
- `diseases` (optional) — confirmed via HitL
- `should_include_null_diseases` — confirmed with user (default: NO)

**Project Mode** (passed by orchestrator after loading report_filters):
- `project_id` — resolved from project name
- `start_date`, `end_date` — provided by user
- `brand_ids` — from `report_filters_brands`
- `disease_only_ids` — disease_ids where indication_id IS NULL in `report_filters_indications_diseases`
- `specific_indication_ids` — indication_ids where indication_id IS NOT NULL
- `search_type(s)` — run both SPONSORED_AD and ORGANIC by default in Project Mode

## References
- Base template: `dtaa/references/sov_base_template.md`
- Project Mode SQL patterns: `dtaa/references/project_mode.md`
- Schema: `dtaa/references/schema.md`
- Guidelines: `dtaa/references/guidelines.md`
