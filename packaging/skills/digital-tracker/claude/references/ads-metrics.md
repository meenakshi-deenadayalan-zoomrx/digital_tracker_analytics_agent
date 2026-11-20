
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

> **Note**: The historical local reader rejected CTEs (`WITH`); the native remote WITH/SELECT compatibility probe succeeded. Keep this nested-subquery equivalent. This query scans the
> filtered ads once. The earlier four-scan template exceeded the read replica's
> statement timeout for a full year.

Fill `{brand_normalization}` with one or more `WHEN ... THEN ...` clauses for
the confirmed labels. When no normalization is needed, use
`WHEN 1 = 0 THEN NULL`; leaving it empty makes the `CASE` expression invalid.

```sql
-- Ads SOV among the confirmed brand labels; no CTEs and one ad scan.
-- The total_users divisor includes zero-exposure user/brand pairs.
SELECT brand_name,
       ROUND(SUM(brand_items / NULLIF(total_items, 0)) / MAX(total_users) * 100, 2) AS sov_percentage,
       COUNT(DISTINCT user_id) AS reach,
       SUM(brand_items) AS total_brand_exposures,
       ROUND(SUM(brand_items) / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS frequency
FROM (
    SELECT user_id, brand_name, brand_items,
           SUM(brand_items) OVER (PARTITION BY user_id) AS total_items,
           MAX(user_seq) OVER () AS total_users
    FROM (
        SELECT user_id, brand_name, COUNT(*) AS brand_items,
               DENSE_RANK() OVER (ORDER BY user_id) AS user_seq
        FROM (
            SELECT ct.id AS item_id, ct.user_id,
                   GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END
                                ORDER BY bt.standard_name) AS brand_name
            FROM perxcept_extension.ads ct
            JOIN perxcept_extension.users u ON ct.user_id = u.id
            JOIN perxcept_extension.project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN perxcept_extension.user_speciality_mappings usm ON ct.user_id = usm.user_id
            JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = ct.id AND ga.entity_type = 'AD'
            JOIN perxcept_extension.gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN perxcept_extension.brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE ct.created >= '{start_date} 00:00:00'
              AND ct.created < DATE_ADD('{end_date}', INTERVAL 1 DAY)
              AND ct.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY ct.id, ct.user_id
        ) ads_by_brand
        GROUP BY user_id, brand_name
    ) user_brand
) scored
GROUP BY brand_name
ORDER BY sov_percentage DESC
LIMIT 50;
```

## 2D SOV (Brand × Website)

Keep `total_items` partitioned by `user_id` alone, across all websites. Add
`dimension` to the ad-level SELECT and GROUP BY, carry it through the
user-brand aggregation, and group the outer result by brand and dimension.
The `total_users` divisor still includes every eligible user, including those
with zero exposures for a given brand/website pair.

```sql
-- In ads_by_brand SELECT and GROUP BY:
LEFT JOIN perxcept_extension.web_contents wc ON ct.web_content_id = wc.id
LEFT JOIN perxcept_extension.tracked_urls turl ON wc.tracked_url_id = turl.id
-- Add: COALESCE(turl.url, 'Non-HC') AS dimension
-- GROUP BY ct.id, ct.user_id, dimension
-- In user_brand: GROUP BY user_id, brand_name, dimension
-- In scored: SUM(brand_items) OVER (PARTITION BY user_id), without dimension
-- In outer SELECT and GROUP BY: brand_name, dimension
```

## Disease Filter Patterns

```sql
-- With disease filter (default):
LEFT JOIN perxcept_extension.gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN perxcept_extension.disease_terms dt ON gad.disease_id = dt.id
-- WHERE: AND LOWER(dt.standard_name) REGEXP '{disease_regex}'

-- With TA agnostic included:
-- WHERE: AND (LOWER(dt.standard_name) REGEXP '{disease_regex}' OR dt.standard_name IS NULL)

-- Without disease filter:
-- Remove disease joins and WHERE conditions
```

## Required Parameters
- `project_id` — from `projects` table (confirm via HitL)
- `start_date`, `end_date` — in 'YYYY-MM-DD' format
- `brands` — list confirmed via HitL discovery
- `diseases` (optional) — confirmed via HitL
- `should_include_null_diseases` — confirmed with user (default: NO)

## References
- Base template (CTE + no-CTE reference): `references/sov_base_template.md`
- Schema: `references/schema.md`
- Guidelines: `references/guidelines.md`
