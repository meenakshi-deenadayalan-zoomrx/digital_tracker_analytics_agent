
# DTAA — Posts Channel Metrics (SOV, Reach, Frequency)

## Metrics Supported
- **Share of Voice (SOV)**: Brand's average share of posts seen per target user, relative to all queried brands
- **Reach**: Count of distinct target users who saw a brand's posts
- **Frequency**: Average posts per **reached** user (not per total universe)

## Key Differences from Other Channels
- No direct `user_id` on `posts` — join path: `posts → web_content_posts → web_contents`
- `user_wave_id` filter applies on `web_contents`, not on `posts`
- Date column: `wc.created` (from `web_contents`)
- Entity type: `POST`

## Channel Adaptation (from base template)

| Placeholder | Posts Value |
|-------------|------------|
| Channel join | `posts p JOIN web_content_posts wcp ON wcp.post_id = p.id JOIN web_contents wc ON wcp.web_content_id = wc.id` |
| User reference | `wc.user_id` |
| `{date_column}` | `wc.created` |
| `{ga_join_condition}` | `ga.entity_id = p.id AND ga.entity_type = 'POST'` |
| `user_wave_id filter` | `AND wc.user_wave_id IS NULL` |

## Standard SOV Query (1D — by brand)

> **Note**: The historical local reader rejected CTEs (`WITH`); the native remote WITH/SELECT compatibility probe succeeded. Keep this nested-subquery equivalent. This query uses nested subqueries directly.
> See `references/sov_base_template.md` for the CTE reference version.

```sql
-- Posts SOV — no-CTE, ready for the remote SELECT route
-- item_id = posts.id; user_id via web_contents; user_wave_id on web_contents
-- Frequency = total brand posts / distinct reached users (not universe)
SELECT
    brand_name,
    ROUND(AVG(individual_sov) * 100, 2)                                                       AS sov_percentage,
    SUM(CASE WHEN brand_items > 0 THEN 1 ELSE 0 END)                                         AS reach,
    SUM(brand_items)                                                                           AS total_brand_posts,
    ROUND(SUM(brand_items) / NULLIF(SUM(CASE WHEN brand_items > 0 THEN 1 ELSE 0 END), 0), 2) AS frequency
FROM (
    SELECT
        au.user_id,
        tb.brand_name,
        COALESCE(uba.brand_items, 0)                    AS brand_items,
        COALESCE(uba.brand_items / uta.total_items, 0)  AS individual_sov
    FROM (SELECT DISTINCT user_id FROM (
            SELECT DISTINCT p.id AS item_id, wc.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM perxcept_extension.posts p
            JOIN perxcept_extension.web_content_posts wcp ON wcp.post_id = p.id
            JOIN perxcept_extension.web_contents wc ON wcp.web_content_id = wc.id
            JOIN perxcept_extension.users u ON wc.user_id = u.id
            JOIN perxcept_extension.project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN perxcept_extension.user_speciality_mappings usm ON wc.user_id = usm.user_id
            JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = p.id AND ga.entity_type = 'POST'
            JOIN perxcept_extension.gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN perxcept_extension.brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE wc.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND wc.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY p.id) cn) au
    CROSS JOIN (SELECT DISTINCT brand_name FROM (
            SELECT DISTINCT p.id AS item_id, wc.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM perxcept_extension.posts p
            JOIN perxcept_extension.web_content_posts wcp ON wcp.post_id = p.id
            JOIN perxcept_extension.web_contents wc ON wcp.web_content_id = wc.id
            JOIN perxcept_extension.users u ON wc.user_id = u.id
            JOIN perxcept_extension.project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN perxcept_extension.user_speciality_mappings usm ON wc.user_id = usm.user_id
            JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = p.id AND ga.entity_type = 'POST'
            JOIN perxcept_extension.gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN perxcept_extension.brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE wc.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND wc.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY p.id) cn) tb
    LEFT JOIN (SELECT user_id, brand_name, COUNT(DISTINCT item_id) AS brand_items FROM (
            SELECT DISTINCT p.id AS item_id, wc.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM perxcept_extension.posts p
            JOIN perxcept_extension.web_content_posts wcp ON wcp.post_id = p.id
            JOIN perxcept_extension.web_contents wc ON wcp.web_content_id = wc.id
            JOIN perxcept_extension.users u ON wc.user_id = u.id
            JOIN perxcept_extension.project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN perxcept_extension.user_speciality_mappings usm ON wc.user_id = usm.user_id
            JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = p.id AND ga.entity_type = 'POST'
            JOIN perxcept_extension.gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN perxcept_extension.brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE wc.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND wc.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY p.id) cn GROUP BY user_id, brand_name) uba
        ON au.user_id = uba.user_id AND tb.brand_name = uba.brand_name
    LEFT JOIN (SELECT user_id, COUNT(DISTINCT item_id) AS total_items FROM (
            SELECT DISTINCT p.id AS item_id, wc.user_id,
                GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
            FROM perxcept_extension.posts p
            JOIN perxcept_extension.web_content_posts wcp ON wcp.post_id = p.id
            JOIN perxcept_extension.web_contents wc ON wcp.web_content_id = wc.id
            JOIN perxcept_extension.users u ON wc.user_id = u.id
            JOIN perxcept_extension.project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}
            JOIN perxcept_extension.user_speciality_mappings usm ON wc.user_id = usm.user_id
            JOIN perxcept_extension.gpt_annotations ga ON ga.entity_id = p.id AND ga.entity_type = 'POST'
            JOIN perxcept_extension.gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
            JOIN perxcept_extension.brand_terms bt ON gab.brand_id = bt.id
            {disease_joins}
            WHERE wc.created BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
              AND wc.user_wave_id IS NULL
              AND usm.speciality_id NOT IN (28, 30)
              AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
              {disease_filter}
            GROUP BY p.id) cn GROUP BY user_id) uta
        ON au.user_id = uta.user_id
) user_brand_sov
GROUP BY brand_name
ORDER BY sov_percentage DESC
LIMIT 50;
```

## Disease Filter Patterns

```sql
-- With disease filter (default):
LEFT JOIN perxcept_extension.gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN perxcept_extension.disease_terms dt ON gad.disease_id = dt.id
-- WHERE: AND LOWER(dt.standard_name) REGEXP '{disease_regex}'

-- With TA agnostic included:
-- WHERE: AND (LOWER(dt.standard_name) REGEXP '{disease_regex}' OR dt.standard_name IS NULL)
```

## 2D SOV (Brand × Account/Platform)

> **⚠️ `uta` denominator rule**: In 2D queries, the `uta` subquery must group by `user_id` ONLY — **never** by the second dimension. The denominator is the user's total posts across all dimensions. Including dimension in `uta`'s GROUP BY breaks SOV.

```sql
-- Add to inner cn subquery SELECT and GROUP BY:
p.account_name AS dimension
-- GROUP BY p.id, dimension
-- In uba: GROUP BY user_id, brand_name, dimension; add dimension to ON
-- In uta: GROUP BY user_id ONLY
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
