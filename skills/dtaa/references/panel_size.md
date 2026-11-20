# Panel Size / Active Users

**Trigger:** the user asks "panel size", "DT panel", "active users", "how many
users / HCPs / oncologists (or any specialty) do we have in the panel", or any
count of the Digital Tracker panel by specialty.

**Rule: answer with ACTIVES over the last 3 months, always.** Never answer with
registered users (`COUNT(*) FROM users`, or `user_speciality_mappings` alone).
Registered counts are ~40x larger and mostly dormant (verified 2026-11-20:
26,535 registered, 22,117 tracking-enabled, but only 649 active in the prior
3 months). Quoting the registered number as "panel size" badly overstates it.

- **Window:** the 3 months ending today, i.e. `created >= CURDATE() - INTERVAL 3 MONTH`
  and `created < CURDATE() + INTERVAL 1 DAY`. Use literal dates in the query.
  If the user gives a different window, use theirs.
- **Active** = a user with at least one tracked item in any of the six
  channels (web pages, emails, ads, posts, search ads, AI overview/mode).
  Same definition and exclusions as `actives_across_channel.md`:
  `user_wave_id IS NULL` on every branch except emails; ads whose parent
  web_content is an `EMAIL_CAMPAIGN` excluded; specialty IDs 28 (Test Users)
  and 30 (Removed Users) excluded.
- **Specialty split:** join `user_speciality_mappings` / `specialities`.
  A user mapped to several specialties counts in each, so per-specialty rows
  can sum to more than the distinct total. Report the distinct total separately.
- **Patient cohorts:** specialties 29 (gMG Patients) and 32 (Alzheimer's
  Patients) are patients, not HCPs. Report the HCP-only total (exclude
  28, 30, 29, 32) and say which was used.
- No entity names involved, so the HitL confirmation is not needed. State the
  window you used in the reply.
- Also mention registered / tracking-enabled counts only as context, clearly
  labelled, never as the headline.

## Query (no CTE; per-branch DISTINCT user_id, UNION, then specialty join)

Replace `{S}` with the window start and `{E}` with the day after today.

```sql
SELECT spec.id, spec.speciality, COUNT(DISTINCT a.user_id) AS active_users
FROM (
  SELECT user_id FROM web_contents
    WHERE type IN ('WEB_PAGE','HTML_WEB_PAGE') AND user_wave_id IS NULL
      AND created >= '{S}' AND created < '{E}'
  UNION
  SELECT user_id FROM web_contents
    WHERE type = 'EMAIL_CAMPAIGN' AND created >= '{S}' AND created < '{E}'
  UNION
  SELECT a1.user_id FROM ads a1
    LEFT JOIN web_contents w1 ON w1.id = a1.web_content_id
    WHERE a1.user_wave_id IS NULL AND (w1.type != 'EMAIL_CAMPAIGN' OR w1.type IS NULL)
      AND a1.created >= '{S}' AND a1.created < '{E}'
  UNION
  SELECT w2.user_id FROM web_content_posts p
    JOIN web_contents w2 ON w2.id = p.web_content_id
    WHERE w2.user_wave_id IS NULL AND p.created >= '{S}' AND p.created < '{E}'
  UNION
  SELECT q.user_id FROM search_results sr
    JOIN search_queries q ON q.id = sr.search_query_id
    WHERE sr.type = 'SPONSORED_AD' AND q.user_wave_id IS NULL
      AND sr.created >= '{S}' AND sr.created < '{E}'
  UNION
  SELECT q2.user_id FROM ai_responses ar
    JOIN search_queries q2 ON q2.id = ar.search_query_id
    WHERE q2.user_wave_id IS NULL AND ar.created >= '{S}' AND ar.created < '{E}'
) a
JOIN user_speciality_mappings m ON m.user_id = a.user_id
JOIN specialities spec ON spec.id = m.speciality_id
WHERE spec.id NOT IN (28,30)
GROUP BY spec.id, spec.speciality
ORDER BY active_users DESC;
```

Distinct totals: reuse the same derived table `a`, `LEFT JOIN
user_speciality_mappings m`, and select
`COUNT(DISTINCT a.user_id)` (all), `COUNT(DISTINCT CASE WHEN m.speciality_id NOT IN (28,30) THEN a.user_id END)`
(excl. internal) and the same with `NOT IN (28,30,29,32)` (HCP only).

Single-specialty question ("how many oncologists"): add
`AND spec.speciality = 'Hematology/Oncology'` (oncology = `Hematology/Oncology`,
id 1) and return that one number plus the window.

## Reference result: 2026-08-20 to 2026-11-20

Distinct active users: 649 total, 643 excl. test/removed, 642 HCP-only.

| Specialty | Active |
|---|---:|
| Hematology/Oncology | 165 |
| NP/PA/RN | 161 |
| Primary Care | 103 |
| Gastroenterology | 78 |
| Pediatrics | 70 |
| Urology | 27 |
| Infectious Diseases | 14 |
| Allergy/Immunology | 9 |
| Dermatology | 3 |
| Other | 3 |
| Neurology | 2 |
| Surgery, Cardiology, Pulmonology, Hepatology, Nephrology, Radiology, Pharmacist, gMG Patients | 1 each |

Many specialties with thousands of registered users show near-zero actives
(e.g. Alzheimer's Patients 3,738 registered, 0 active). That is expected.
