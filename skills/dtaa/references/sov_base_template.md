# SOV Base Template — Shared Methodology

All channel-metrics skills adapt this template by substituting the channel-specific values listed in the **Adaptation Guide** at the bottom.

## Methodology: CROSS JOIN (Average User SOV)

SOV is computed as the **average individual user SOV** across **all users who saw any content** in the period — not just users who saw a specific brand. Users who saw no content for Brand X contribute **0** to Brand X's average. This matches the production `calculate_brand_share_of_voice` tool and gives a fair, universe-level SOV.

> **Old approach (deprecated)**: simple JOIN between `user_brand_exposures` and `user_total_exposures` — excluded zero-exposure users, inflating SOV for niche brands.

---

## 1D SOV Template (Brand ranking by Share of Voice)

```sql
-- 1D Brand SOV for {CHANNEL} channel
-- CROSS JOIN ensures all active users contribute to each brand's SOV average
WITH target_users AS (
    SELECT DISTINCT u.id AS user_id
    FROM users u
    JOIN project_target_list ptl ON u.npi = ptl.npi
    JOIN user_speciality_mappings usm ON u.id = usm.user_id
    WHERE ptl.project_id = {project_id}
      AND usm.speciality_id NOT IN (28, 30)
),
-- Normalize brand names; GROUP_CONCAT collapses multi-brand annotations per item
channel_normalized AS (
    SELECT DISTINCT
        ct.id AS item_id,
        ct.user_id,
        GROUP_CONCAT(DISTINCT
            CASE
                {brand_normalization}   -- WHEN LOWER(bt.standard_name) REGEXP '...' THEN 'Canonical Name'
                ELSE bt.standard_name
            END
        ) AS brand_name
    FROM {channel_table} ct
    JOIN target_users tu ON ct.user_id = tu.user_id
    {annotation_join}
    JOIN gpt_annotations ga ON {ga_join_condition}
    JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
    JOIN brand_terms bt ON gab.brand_id = bt.id
    {disease_joins}
    WHERE ct.{date_column} BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
      AND ct.user_wave_id IS NULL
      AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
      {disease_filter}
    GROUP BY ct.id
),
-- CROSS JOIN: pair every active user with every brand (zeros for non-exposure combos)
brand_sov AS (
    SELECT
        brand_name,
        AVG(individual_sov) * 100                             AS avg_user_sov,
        SUM(CASE WHEN brand_items > 0 THEN 1 ELSE 0 END)     AS reach,
        SUM(brand_items)                                      AS total_brand_exposures,
        SUM(brand_items) / COUNT(DISTINCT user_id)            AS frequency
    FROM (
        SELECT
            au.user_id,
            tb.brand_name,
            COALESCE(uba.brand_items, 0)                      AS brand_items,
            COALESCE(uba.brand_items / uta.total_items, 0)    AS individual_sov
        FROM (
            SELECT DISTINCT user_id FROM channel_normalized
        ) au
        CROSS JOIN (
            SELECT DISTINCT brand_name FROM channel_normalized
        ) tb
        LEFT JOIN (
            SELECT user_id, brand_name, COUNT(DISTINCT item_id) AS brand_items
            FROM channel_normalized
            GROUP BY user_id, brand_name
        ) uba ON au.user_id = uba.user_id AND tb.brand_name = uba.brand_name
        LEFT JOIN (
            SELECT user_id, COUNT(DISTINCT item_id) AS total_items
            FROM channel_normalized
            GROUP BY user_id
        ) uta ON au.user_id = uta.user_id
    ) user_brand_sov
    GROUP BY brand_name
)
SELECT
    brand_name,
    ROUND(avg_user_sov, 2)          AS sov_percentage,
    reach,
    total_brand_exposures,
    ROUND(frequency, 2)             AS frequency
FROM brand_sov
ORDER BY sov_percentage DESC;
```

---

## 2D SOV Template (Brand SOV split by a second dimension)

```sql
-- 2D Brand SOV — adds {second_dimension} (e.g., website domain, date, rank)
-- Same CROSS JOIN methodology; dimension added to channel_normalized and throughout
WITH target_users AS (
    -- same as 1D
),
channel_normalized AS (
    SELECT DISTINCT
        ct.id AS item_id,
        ct.user_id,
        {second_dimension_expr} AS dimension,   -- e.g., DATE(ct.created), sr.type, tu.url
        GROUP_CONCAT(DISTINCT
            CASE
                {brand_normalization}
                ELSE bt.standard_name
            END
        ) AS brand_name
    FROM {channel_table} ct
    -- same joins as 1D
    GROUP BY ct.id, dimension   -- add dimension to GROUP BY
),
brand_sov AS (
    SELECT
        brand_name,
        dimension,
        AVG(individual_sov) * 100                             AS avg_user_sov,
        SUM(CASE WHEN brand_items > 0 THEN 1 ELSE 0 END)     AS reach,
        SUM(brand_items)                                      AS total_brand_exposures,
        SUM(brand_items) / COUNT(DISTINCT user_id)            AS frequency
    FROM (
        SELECT
            au.user_id,
            td.brand_name,
            td.dimension,
            COALESCE(uba.brand_items, 0)                      AS brand_items,
            COALESCE(uba.brand_items / uta.total_items, 0)    AS individual_sov
        FROM (
            SELECT DISTINCT user_id FROM channel_normalized
        ) au
        CROSS JOIN (
            SELECT DISTINCT brand_name, dimension FROM channel_normalized
        ) td
        LEFT JOIN (
            SELECT user_id, brand_name, dimension, COUNT(DISTINCT item_id) AS brand_items
            FROM channel_normalized
            GROUP BY user_id, brand_name, dimension
        ) uba ON au.user_id = uba.user_id AND td.brand_name = uba.brand_name AND td.dimension = uba.dimension
        LEFT JOIN (
            SELECT user_id, COUNT(DISTINCT item_id) AS total_items
            FROM channel_normalized
            GROUP BY user_id
        ) uta ON au.user_id = uta.user_id
    ) user_brand_dim_sov
    GROUP BY brand_name, dimension
)
SELECT
    brand_name,
    dimension,
    ROUND(avg_user_sov, 2)          AS sov_percentage,
    reach,
    total_brand_exposures,
    ROUND(frequency, 2)             AS frequency
FROM brand_sov
ORDER BY brand_name, sov_percentage DESC;
```

---

## Critical: No-CTE Rewrite (MCP Tool Requirement)

The `dtsa_mysql_read` tool **rejects queries starting with `WITH`** (CTEs). All queries MUST be written as deeply nested subqueries. The CTE templates above are for readability only — always convert before execution.

The `channel_normalized` subquery must be **repeated 4 times** (identical copy in `au`, `tb`, `uba`, and `uta`).

```sql
-- No-CTE pattern for 1D SOV
SELECT
    brand_name,
    ROUND(AVG(individual_sov) * 100, 2) AS sov_percentage,
    SUM(CASE WHEN brand_items > 0 THEN 1 ELSE 0 END) AS reach,
    SUM(brand_items) AS total_brand_exposures,
    ROUND(SUM(brand_items) / COUNT(DISTINCT user_id), 2) AS frequency
FROM (
    SELECT
        au.user_id,
        tb.brand_name,
        COALESCE(uba.brand_items, 0) AS brand_items,
        COALESCE(uba.brand_items / uta.total_items, 0) AS individual_sov
    FROM (
        SELECT DISTINCT user_id FROM (
            SELECT DISTINCT ct.id AS item_id, ct.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM {channel_table} ct
            JOIN users u ON ct.user_id = u.id
            JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN user_speciality_mappings usm ON ct.user_id = usm.user_id
            JOIN gpt_annotations ga ON {ga_join_condition}
            JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE ct.{date_column} BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND ct.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY ct.id
        ) cn
    ) au
    CROSS JOIN (
        SELECT DISTINCT brand_name FROM (
            SELECT DISTINCT ct.id AS item_id, ct.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM {channel_table} ct
            JOIN users u ON ct.user_id = u.id
            JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN user_speciality_mappings usm ON ct.user_id = usm.user_id
            JOIN gpt_annotations ga ON {ga_join_condition}
            JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE ct.{date_column} BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND ct.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY ct.id
        ) cn
    ) tb
    LEFT JOIN (
        SELECT user_id, brand_name, COUNT(DISTINCT item_id) AS brand_items
        FROM (
            SELECT DISTINCT ct.id AS item_id, ct.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM {channel_table} ct
            JOIN users u ON ct.user_id = u.id
            JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN user_speciality_mappings usm ON ct.user_id = usm.user_id
            JOIN gpt_annotations ga ON {ga_join_condition}
            JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE ct.{date_column} BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND ct.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY ct.id
        ) cn GROUP BY user_id, brand_name
    ) uba ON au.user_id = uba.user_id AND tb.brand_name = uba.brand_name
    LEFT JOIN (
        SELECT user_id, COUNT(DISTINCT item_id) AS total_items
        FROM (
            SELECT DISTINCT ct.id AS item_id, ct.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM {channel_table} ct
            JOIN users u ON ct.user_id = u.id
            JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN user_speciality_mappings usm ON ct.user_id = usm.user_id
            JOIN gpt_annotations ga ON {ga_join_condition}
            JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE ct.{date_column} BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND ct.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY ct.id
        ) cn GROUP BY user_id
    ) uta ON au.user_id = uta.user_id
) user_brand_sov
GROUP BY brand_name
ORDER BY sov_percentage DESC;
```

> **2D SOV — `uta` denominator rule**: The `uta` subquery groups by `user_id` ONLY — **never by dimension**. The denominator is the user's total items across all dimensions combined. Including dimension in `uta`'s GROUP BY makes each cell divide by items-within-that-dimension rather than total items, breaking the SOV calculation (values will not sum to ~100%).

> **Ads → website dimension — use LEFT JOIN**: Many ads have `web_content_id = NULL`. When joining `ads → web_contents → tracked_urls` for a website dimension, always use `LEFT JOIN web_contents wc ON a.web_content_id = wc.id` and `LEFT JOIN tracked_urls tu ON wc.tracked_url_id = tu.id`. An INNER JOIN silently drops all NULL-web_content_id ads (~96% for some projects), making "Non-HC" and other website categories show zero or near-zero values.

---

## Disease Filter Patterns

### With disease filter (default):
```sql
-- In JOIN section:
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN disease_terms dt ON gad.disease_id = dt.id
-- In WHERE section:
AND LOWER(dt.standard_name) REGEXP '{disease_regex}'
```

### With disease filter + TA agnostic (should_include_null_diseases=true):
```sql
-- In WHERE section:
AND (LOWER(dt.standard_name) REGEXP '{disease_regex}' OR dt.standard_name IS NULL)
```

### Without disease filter (no disease annotation filtering):
```sql
-- No gpt_annotations_diseases join needed
-- Remove disease-related WHERE conditions
```

---

## Reach & Frequency Standalone

When user asks for Reach/Frequency without SOV:
```sql
SELECT
    bt.standard_name AS brand,
    COUNT(DISTINCT ct.user_id)                                   AS reach,
    COUNT(DISTINCT ct.id)                                        AS total_exposures,
    ROUND(COUNT(DISTINCT ct.id) / COUNT(DISTINCT ct.user_id), 2) AS frequency
FROM {channel_table} ct
JOIN user_speciality_mappings usm ON ct.user_id = usm.user_id
{annotation_join}
JOIN gpt_annotations ga ON {ga_join_condition}
JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
JOIN brand_terms bt ON gab.brand_id = bt.id
WHERE ct.{date_column} BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
  AND ct.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
  {optional_project_filter}
  {disease_filter}
GROUP BY bt.standard_name
ORDER BY reach DESC;
```

---

## Adaptation Guide for Channel Skills

| Channel | `channel_table` | `date_column` | `ga_join_condition` | `annotation_join` |
|---------|----------------|---------------|---------------------|-------------------|
| Ads | `ads ct` | `created` | `ga.entity_id = ct.id AND ga.entity_type = 'AD'` | *(none extra)* |
| Emails | `emails ct` | `received_date` | `ga.entity_id = ct.id AND ga.entity_type = 'EMAIL'` | *(none extra)* |
| Posts | `web_content_posts wcp JOIN web_contents wc ON wcp.web_content_id = wc.id JOIN posts ct ON wcp.post_id = ct.id` | `wc.created` | `ga.entity_id = ct.id AND ga.entity_type = 'POST'` | See posts join |
| Search (ads) | `search_results ct` | `created` | `ga.entity_id = ct.id AND ga.entity_type = 'SEARCH_AD'` | `AND ct.type = 'SPONSORED_AD'` |
| Search (organic) | `search_results ct` | `created` | `ga.entity_id = ct.id AND ga.entity_type = 'SEARCH_RESULT'` | `AND ct.type IN ('ORGANIC','AI_REFERENCE')` |
| Web (Share of Attention) | See `dtaa-web-metrics` | `wc.created` | `ga.entity_id = wcg.id AND ga.entity_type = 'WEB_CONTENT_GROUP'` | See web metrics skill |

**user_wave_id note**: Posts channel — apply `wc.user_wave_id IS NULL` on `web_contents`, not on `posts`. Emails — no `user_wave_id` column on `emails` table. Search — no `user_wave_id` column on `search_results`; apply `sq.user_wave_id IS NULL` on `search_queries` only if that table is joined.
