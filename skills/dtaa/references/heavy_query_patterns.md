# Heavy Query Patterns

How to write large multi-channel or per-NPI queries without hitting the
`dtsa_mysql_read` statement timeout (MySQL error 3024, "max statement execution
time exceeded").

The failure mode is specific: each half of a query runs fine alone, and the
combination times out. That is the signal to reach for the patterns below rather
than to retry.

## Tool constraints

| Constraint | Detail |
|---|---|
| Statement timeout | Error 3024 on long-running queries |
| No CTEs | `WITH` is rejected — nested subqueries only |
| Row cap | 100 rows returned |
| Window functions | **Supported** — `ROW_NUMBER`, `SUM`/`COUNT` `OVER` all work |

## Panel filter: `EXISTS`, not a `DISTINCT` subquery

```sql
-- correct — evaluated per row, no materialization
WHERE EXISTS (
  SELECT 1 FROM project_target_list ptl
  WHERE ptl.npi = u.npi AND ptl.project_id IN (...)
)

-- expensive — re-materializes once per channel arm
JOIN (SELECT DISTINCT npi FROM project_target_list WHERE project_id IN (...)) p
  ON p.npi = u.npi
```

A cross-channel query unions 5–6 arms. The `DISTINCT` subquery is rebuilt for
each one — roughly 7× the cost, and the single largest contributor to timeouts.

## Disease filter: materialized id→group map

Keep `REGEXP` off the per-annotation hot path by resolving disease names to ids
once, then joining on the integer:

```sql
JOIN (
  SELECT id, CASE WHEN LOWER(standard_name) REGEXP '...' THEN 'GroupA' ... END AS grp
  FROM disease_terms
  WHERE LOWER(standard_name) REGEXP '...'
) dmap ON gadbw.disease_id = dmap.id
```

## Run per disease

For per-disease tables, execute one query per disease (one `dmap` regexp each).
The pooled all-diseases version fits only when it does **not** also carry the
separate all-web scan described below.

## Avoid the separate all-web denominator scan

For web Share of Attention, compute the denominator from rows already scanned:

```sql
brand_seconds / SUM(brand_seconds) OVER (PARTITION BY user_id, disease_grp)
```

That gives a **within-disease** denominator. Adding a separate
`SUM(...)` over all `web_contents` as a total reliably times out. If the analysis
genuinely needs an all-web denominator, run it as its own query and join the
results outside the database.

## Grouped median without a median function

MySQL has no `MEDIAN`. Use row numbering, which handles both odd and even counts:

```sql
-- inner: number the rows
ROW_NUMBER() OVER (PARTITION BY grp ORDER BY val) AS rn,
COUNT(*)     OVER (PARTITION BY grp)              AS cnt

-- outer: average the middle one or two
AVG(CASE WHEN rn IN (FLOOR((cnt+1)/2), FLOOR((cnt+2)/2)) THEN val END) AS median_val
```

## Annotation join differs by channel

| Channel | Join path |
|---|---|
| Web contents | `gpt_annotations_disease_brand_weights` — `brand_id`, `disease_id`, `weight` in one table |
| All others | `gpt_annotations_brands` + `gpt_annotations_diseases` separately |

For `WEB_CONTENT_GROUP` annotations, `gpt_annotations_brands` exists but holds
**zero** brand rows — joining it returns nothing. `gpt_annotations_diseases_brands`
does not exist at all. See `dtaa-web-metrics` for the full web template.
