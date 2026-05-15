---
name: "DTAA Web Metrics"
description: "Web contents channel metrics: Share of Attention, Reach, and Frequency. Activate when user asks for Share of Attention, brand time-spent analysis, or web-specific reach/frequency. Share of Attention = weighted duration, NOT raw page counts."
---

# DTAA — Web Contents Metrics (Share of Attention, Reach, Frequency)

## Metrics Supported
- **Share of Attention (SoA)**: Brand's weighted time-share among target users (duration × annotation weight)
- **Reach**: Count of distinct target users who visited brand-relevant content
- **Frequency**: Average visits per **reached** user (not per total universe)

## Why Share of Attention (Not SOV)
Web contents captures page duration — a user spending 10 minutes on a brand page is more valuable than a 10-second visit. SOV counts exposures; SoA weights by time × annotation weight.

Each web content group can mention multiple brands with different weights (from `gpt_annotations_disease_brand_weights.weight`). A page with 60% brand A weight and 40% brand B weight contributes accordingly to each brand's attention.

## Annotation Join Path (Unique to Web)
```
web_contents → web_content_groups → gpt_annotations (entity_type='WEB_CONTENT_GROUP')
                                   → gpt_annotations_disease_brand_weights (brand_id + disease_id + weight)
                                   → brand_terms ON gadbw.brand_id = bt.id
                                   → disease_terms ON gadbw.disease_id = dt.id
```

> **⚠️ Critical**: For WEB_CONTENT_GROUP annotations, `gpt_annotations_brands` is NOT populated (returns 0 rows). The table `gpt_annotations_diseases_brands` does not exist. Use `gpt_annotations_disease_brand_weights` as the single join for brand, disease, and weight.

## Standard Share of Attention Query (1D — by brand)

> **Note**: `dtsa_mysql_read` rejects CTEs (`WITH`). This query uses nested subqueries directly.
> See `dtaa/references/sov_base_template.md` for the CTE reference version.
>
> **SoA differs from SOV**: The inner subquery pre-aggregates to (user_id, brand_name) level
> (not per item_id). `uta` is a separate total-duration subquery, not a repeat of the brand subquery.

```sql
-- Web Share of Attention — no-CTE, ready for dtsa_mysql_read
-- Frequency = total visits / distinct reached users (not universe)
SELECT
    brand_name,
    ROUND(AVG(individual_soa) * 100, 2)                                                        AS share_of_attention_pct,
    SUM(CASE WHEN brand_seconds > 0 THEN 1 ELSE 0 END)                                        AS reach,
    ROUND(SUM(brand_seconds) / 3600, 2)                                                        AS total_weighted_hours,
    ROUND(SUM(visits) / NULLIF(SUM(CASE WHEN brand_seconds > 0 THEN 1 ELSE 0 END), 0), 2)    AS frequency
FROM (
    SELECT
        au.user_id,
        tb.brand_name,
        COALESCE(wbd.brand_seconds, 0)                      AS brand_seconds,
        COALESCE(wbd.visits, 0)                             AS visits,
        COALESCE(wbd.brand_seconds / utd.total_seconds, 0)  AS individual_soa
    FROM (SELECT DISTINCT user_id FROM (
            SELECT wc.user_id,
                CASE {brand_normalization} ELSE bt.standard_name END AS brand_name,
                SUM(TIME_TO_SEC(wc.duration) * COALESCE(gadbw.weight, 1)) AS brand_seconds,
                COUNT(DISTINCT wc.id) AS visits
            FROM users u
            JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN user_speciality_mappings usm ON u.id = usm.user_id
            JOIN web_contents wc ON u.id = wc.user_id
            JOIN web_content_groups wcg ON wc.web_content_group_id = wcg.id
            JOIN gpt_annotations ga ON ga.entity_id = wcg.id AND ga.entity_type = 'WEB_CONTENT_GROUP'
            JOIN gpt_annotations_disease_brand_weights gadbw ON gadbw.gpt_annotation_id = ga.id
            JOIN brand_terms bt ON gadbw.brand_id = bt.id
            {disease_joins}
            WHERE wc.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
              AND wc.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY wc.user_id, brand_name) wbd_src) au
    CROSS JOIN (SELECT DISTINCT brand_name FROM (
            SELECT wc.user_id,
                CASE {brand_normalization} ELSE bt.standard_name END AS brand_name,
                SUM(TIME_TO_SEC(wc.duration) * COALESCE(gadbw.weight, 1)) AS brand_seconds,
                COUNT(DISTINCT wc.id) AS visits
            FROM users u
            JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN user_speciality_mappings usm ON u.id = usm.user_id
            JOIN web_contents wc ON u.id = wc.user_id
            JOIN web_content_groups wcg ON wc.web_content_group_id = wcg.id
            JOIN gpt_annotations ga ON ga.entity_id = wcg.id AND ga.entity_type = 'WEB_CONTENT_GROUP'
            JOIN gpt_annotations_disease_brand_weights gadbw ON gadbw.gpt_annotation_id = ga.id
            JOIN brand_terms bt ON gadbw.brand_id = bt.id
            {disease_joins}
            WHERE wc.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
              AND wc.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY wc.user_id, brand_name) wbd_src) tb
    LEFT JOIN (
        SELECT wc.user_id,
            CASE {brand_normalization} ELSE bt.standard_name END AS brand_name,
            SUM(TIME_TO_SEC(wc.duration) * COALESCE(gadbw.weight, 1)) AS brand_seconds,
            COUNT(DISTINCT wc.id) AS visits
        FROM users u
        JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
        JOIN user_speciality_mappings usm ON u.id = usm.user_id
        JOIN web_contents wc ON u.id = wc.user_id
        JOIN web_content_groups wcg ON wc.web_content_group_id = wcg.id
        JOIN gpt_annotations ga ON ga.entity_id = wcg.id AND ga.entity_type = 'WEB_CONTENT_GROUP'
        JOIN gpt_annotations_disease_brand_weights gadbw ON gadbw.gpt_annotation_id = ga.id
        JOIN brand_terms bt ON gadbw.brand_id = bt.id
        {disease_joins}
        WHERE wc.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
          AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
          AND wc.user_wave_id IS NULL
          AND usm.speciality_id NOT IN (28, 30)
          AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
          {disease_filter}
        GROUP BY wc.user_id, brand_name) wbd
        ON au.user_id = wbd.user_id AND tb.brand_name = wbd.brand_name
    LEFT JOIN (
        SELECT wc.user_id, SUM(TIME_TO_SEC(wc.duration)) AS total_seconds
        FROM users u
        JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
        JOIN user_speciality_mappings usm ON u.id = usm.user_id
        JOIN web_contents wc ON u.id = wc.user_id
        WHERE wc.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
          AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
          AND wc.user_wave_id IS NULL
          AND usm.speciality_id NOT IN (28, 30)
        GROUP BY wc.user_id) utd
        ON au.user_id = utd.user_id
) user_brand_soa
GROUP BY brand_name
ORDER BY share_of_attention_pct DESC;
```

## Disease Join Patterns for Web

> `gpt_annotations_disease_brand_weights` already carries `disease_id` — no separate `gpt_annotations_diseases` join is needed. Resolve disease name directly from `gadbw.disease_id`.

```sql
-- With disease filter (default):
-- {disease_joins}: JOIN disease_terms dt ON gadbw.disease_id = dt.id
-- {disease_filter}: AND LOWER(dt.standard_name) REGEXP '{disease_regex}'

-- With TA agnostic included (include content not tied to a specific disease):
-- {disease_joins}: LEFT JOIN disease_terms dt ON gadbw.disease_id = dt.id
-- {disease_filter}: AND (LOWER(dt.standard_name) REGEXP '{disease_regex}' OR gadbw.disease_id IS NULL)

-- Without disease filter:
-- {disease_joins}: (empty — gadbw already joined, no disease_terms needed)
-- {disease_filter}: (empty)
```

## 2D Share of Attention (Brand × Website)

> **⚠️ `utd` denominator rule**: In 2D queries, the `utd` (total duration) subquery must group by `user_id` ONLY — **never** by dimension. The denominator is total seconds across ALL web pages. Including dimension in `utd`'s GROUP BY makes each cell divide by duration-within-that-dimension, breaking SoA.

Add to the brand subquery (`wbd_src`) SELECT and GROUP BY:
```sql
LEFT JOIN tracked_urls turl ON wc.tracked_url_id = turl.id
COALESCE(turl.url, 'Unknown') AS dimension
-- GROUP BY wc.user_id, brand_name, dimension
-- In CROSS JOIN tb: SELECT DISTINCT brand_name, dimension
-- In wbd LEFT JOIN: add dimension to ON condition
-- In utd: GROUP BY wc.user_id ONLY
```

## Standalone Reach & Frequency (without SoA)

```sql
SELECT
    bt.standard_name AS brand,
    COUNT(DISTINCT wc.user_id) AS reach,
    COUNT(DISTINCT wc.id) AS total_visits,
    ROUND(COUNT(DISTINCT wc.id) / NULLIF(COUNT(DISTINCT wc.user_id), 0), 2) AS frequency
FROM web_contents wc
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN web_content_groups wcg ON wc.web_content_group_id = wcg.id
JOIN gpt_annotations ga ON ga.entity_id = wcg.id AND ga.entity_type = 'WEB_CONTENT_GROUP'
JOIN gpt_annotations_disease_brand_weights gadbw ON gadbw.gpt_annotation_id = ga.id
JOIN brand_terms bt ON gadbw.brand_id = bt.id
WHERE wc.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
  AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
GROUP BY bt.standard_name
ORDER BY reach DESC;
```

## Sample Size Query

Run this after every SoA query. Use the same filters as the main query.

```sql
-- Run 1: TL size
SELECT COUNT(DISTINCT npi) AS tl_size FROM project_target_list WHERE project_id = {project_id}

-- Run 2: Universe N + total visits
SELECT COUNT(DISTINCT wc.user_id) AS n_hcps_reached, COUNT(DISTINCT wc.id) AS n_total_visits
FROM web_contents wc
JOIN users u ON wc.user_id = u.id
JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
JOIN web_content_groups wcg ON wc.web_content_group_id = wcg.id
JOIN gpt_annotations ga ON ga.entity_id = wcg.id AND ga.entity_type = 'WEB_CONTENT_GROUP'
JOIN gpt_annotations_disease_brand_weights gadbw ON gadbw.gpt_annotation_id = ga.id
JOIN brand_terms bt ON gadbw.brand_id = bt.id
{disease_joins}
WHERE wc.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
  AND wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
  {disease_filter}
```

Display below the results table:
```
**Sample Sizes**
- TL: {tl_size} HCPs
- Universe N (HCPs with ≥1 visit): {n_hcps_reached}
- Total visits: {n_total_visits}
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
