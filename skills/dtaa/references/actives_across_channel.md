# Actives Query across Channel

**Trigger:** the user supplies a target list (TL) of NPIs (CSV, XLSX, or a
pasted list) and asks for "actives across channel" (also "actives", "active
HCPs", "who was active", "activity across channels") for that list.

**What it answers:** which NPIs in the TL produced any tracked activity in a
date window, by channel and by month/quarter. One row per
(client, platform, project, user, speciality, period, channel). The project
join fans rows out, so **report actives as `COUNT(DISTINCT npi)`**, never as
row counts.

## How to run

The MCP read tool caps at 100 rows, so run the bundled script against the
read replica instead. It inlines the NPI list, runs the six channel branches
one at a time, prints the sanity checks, and writes a CSV:

```
.venv/Scripts/python.exe skills/dtaa/scripts/actives_across_channel.py \
    --tl "<path to NPI list>" --start 2026-01-01 --end 2026-06-30 --out <path>.csv
```

`--tl` takes any text file; every 10-digit token is treated as an NPI, so a
header row or extra columns are harmless. If the user wants to run it
themselves in Workbench, pass `--sql <path>` instead of `--out` to emit the
fully inlined query (about 1 MB for a 16k TL, fine for Workbench).

Ask for the date window if the user does not give one. Default to the current
calendar half-year only if they say "this year" or similar.

## Mandatory sanity checks before reporting

The script prints these; always put them in the reply. A TL is usually a
client's full target universe, so most of it is not in the panel at all, and
a small actives count is normal, not a bug:

```sql
-- how much of the TL is even in the panel
SELECT COUNT(DISTINCT npi) FROM users WHERE npi IN ({npis});
-- TL users dropped by the speciality exclusion
SELECT COUNT(DISTINCT u.id) FROM users u
JOIN user_speciality_mappings m ON m.user_id = u.id
WHERE u.npi IN ({npis}) AND m.speciality_id IN (28,30);
```

Report the funnel: NPIs in TL, NPIs in `users`, distinct active NPIs overall,
distinct active NPIs per channel. Example from the HIV TL, Jan-Jun 2026:
16,066 in TL, 490 in users, 11 active.

## Query conventions

Inherited from the team's standard actives query. Do not "fix" them:

- `user_wave_id IS NULL` on every branch except EMAIL (wave captures excluded).
- `spec.id NOT IN (28,30)` on every branch, applied through a LEFT JOIN, so
  users with no speciality mapping are dropped as well.
- ADS excludes ads whose parent web_content is an `EMAIL_CAMPAIGN`.
- EMAIL uses `LEFT JOIN clients`; every other branch uses INNER.
- SEARCH_ADS is `search_results.type = 'SPONSORED_AD'`; AI_Overview/Mode is
  `ai_responses`.
- `project_target_list` / `projects` are LEFT-joined for the project name only.
  The original query filtered `pr.name IN (...)`; this variant replaces that
  filter with `u.npi IN ({npis})`.

Placeholders: `{S}` / `{E}` are the window start and end datetimes, `{npis}`
is the comma-separated NPI list.

## Query template

```sql
SELECT DISTINCT clients.id AS client_id, clients.device_platform, pr.name,
    w.user_id AS user_id, u.npi, speciality,
    CONCAT(MONTH(w.created), '-', YEAR(w.created)) AS period,
    CONCAT('Q', QUARTER(w.created), '''', DATE_FORMAT(w.created, '%y')) AS quarter_year,
    'WEB_PAGE' AS type
FROM web_contents AS w
INNER JOIN users AS u ON w.user_id = u.id
LEFT JOIN project_target_list AS ptl ON u.npi = ptl.npi
LEFT JOIN projects AS pr ON ptl.project_id = pr.id
LEFT JOIN user_speciality_mappings AS usm ON usm.user_id = w.user_id
LEFT JOIN specialities AS spec ON spec.id = speciality_id
INNER JOIN tracked_urls AS t ON t.id = w.tracked_url_id
INNER JOIN clients ON clients.id = w.client_id
WHERE w.type IN ('WEB_PAGE','HTML_WEB_PAGE') AND w.user_wave_id IS NULL
  AND w.created BETWEEN '{S}' AND '{E}'
  AND spec.id NOT IN (28,30) AND u.npi IN ({npis})

UNION ALL
SELECT DISTINCT clients.id, clients.device_platform, pr.name, w.user_id, u.npi, speciality,
    CONCAT(MONTH(w.created), '-', YEAR(w.created)),
    CONCAT('Q', QUARTER(w.created), '''', DATE_FORMAT(w.created, '%y')), 'EMAIL'
FROM web_contents AS w
INNER JOIN users AS u ON w.user_id = u.id
LEFT JOIN project_target_list AS ptl ON u.npi = ptl.npi
LEFT JOIN projects AS pr ON ptl.project_id = pr.id
LEFT JOIN user_speciality_mappings AS usm ON usm.user_id = w.user_id
LEFT JOIN specialities AS spec ON spec.id = speciality_id
LEFT JOIN clients ON clients.id = w.client_id
WHERE w.type = 'EMAIL_CAMPAIGN'
  AND w.created BETWEEN '{S}' AND '{E}'
  AND spec.id NOT IN (28,30) AND u.npi IN ({npis})

UNION ALL
SELECT DISTINCT clients.id, clients.device_platform, pr.name, a.user_id, u.npi, speciality,
    CONCAT(MONTH(a.created), '-', YEAR(a.created)),
    CONCAT('Q', QUARTER(a.created), '''', DATE_FORMAT(a.created, '%y')), 'ADS'
FROM ads AS a
LEFT JOIN web_contents AS w ON w.id = a.web_content_id
INNER JOIN users AS u ON a.user_id = u.id
LEFT JOIN project_target_list AS ptl ON u.npi = ptl.npi
LEFT JOIN projects AS pr ON ptl.project_id = pr.id
LEFT JOIN user_speciality_mappings AS usm ON usm.user_id = a.user_id
LEFT JOIN specialities AS spec ON spec.id = speciality_id
INNER JOIN clients ON clients.id = a.client_id
WHERE a.created BETWEEN '{S}' AND '{E}'
  AND (w.type != 'EMAIL_CAMPAIGN' OR w.type IS NULL) AND a.user_wave_id IS NULL
  AND spec.id NOT IN (28,30) AND u.npi IN ({npis})

UNION ALL
SELECT DISTINCT clients.id, clients.device_platform, pr.name, w.user_id, u.npi, speciality,
    CONCAT(MONTH(wcp.created), '-', YEAR(wcp.created)),
    CONCAT('Q', QUARTER(wcp.created), '''', DATE_FORMAT(wcp.created, '%y')), 'POSTS'
FROM web_content_posts AS wcp
INNER JOIN web_contents AS w ON w.id = wcp.web_content_id
INNER JOIN users AS u ON w.user_id = u.id
LEFT JOIN project_target_list AS ptl ON u.npi = ptl.npi
LEFT JOIN projects AS pr ON ptl.project_id = pr.id
LEFT JOIN user_speciality_mappings AS usm ON usm.user_id = w.user_id
LEFT JOIN specialities AS spec ON spec.id = speciality_id
INNER JOIN clients ON clients.id = w.client_id
WHERE wcp.created BETWEEN '{S}' AND '{E}'
  AND spec.id NOT IN (28,30) AND w.user_wave_id IS NULL AND u.npi IN ({npis})

UNION ALL
SELECT DISTINCT clients.id, clients.device_platform, pr.name, sq.user_id, u.npi, speciality,
    CONCAT(MONTH(sa.created), '-', YEAR(sa.created)),
    CONCAT('Q', QUARTER(sa.created), '''', DATE_FORMAT(sa.created, '%y')), 'SEARCH_ADS'
FROM search_queries AS sq
INNER JOIN search_results AS sa ON sa.search_query_id = sq.id AND sa.type = 'SPONSORED_AD'
INNER JOIN users AS u ON sq.user_id = u.id
LEFT JOIN project_target_list AS ptl ON u.npi = ptl.npi
LEFT JOIN projects AS pr ON ptl.project_id = pr.id
LEFT JOIN user_speciality_mappings AS usm ON usm.user_id = sq.user_id
LEFT JOIN specialities AS spec ON spec.id = speciality_id
INNER JOIN clients ON clients.id = sq.client_id
WHERE sa.created BETWEEN '{S}' AND '{E}'
  AND spec.id NOT IN (28,30) AND sq.user_wave_id IS NULL AND u.npi IN ({npis})

UNION ALL
SELECT DISTINCT clients.id, clients.device_platform, pr.name, sq.user_id, u.npi, speciality,
    CONCAT(MONTH(ar.created), '-', YEAR(ar.created)),
    CONCAT('Q', QUARTER(ar.created), '''', DATE_FORMAT(ar.created, '%y')), 'AI_Overview/Mode'
FROM search_queries AS sq
INNER JOIN ai_responses AS ar ON ar.search_query_id = sq.id
INNER JOIN users AS u ON sq.user_id = u.id
LEFT JOIN project_target_list AS ptl ON u.npi = ptl.npi
LEFT JOIN projects AS pr ON ptl.project_id = pr.id
LEFT JOIN user_speciality_mappings AS usm ON usm.user_id = sq.user_id
LEFT JOIN specialities AS spec ON spec.id = speciality_id
INNER JOIN clients ON clients.id = sq.client_id
WHERE ar.created BETWEEN '{S}' AND '{E}'
  AND spec.id NOT IN (28,30) AND sq.user_wave_id IS NULL AND u.npi IN ({npis});
```

## Output

Deliver the CSV with the columns above, plus the funnel numbers and a
per-channel distinct-NPI table in the reply. Ask where to store the CSV per
the analysis-folder rule before persisting it anywhere.
