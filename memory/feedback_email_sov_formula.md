---
name: Email SOV formula bug fix
description: Email channel SOV must use window function (not AVG individual_sov) and no CTEs
type: feedback
originSessionId: 08a3b9a2-8598-425c-9cc3-7955738bb8f4
---
Use `SUM(exposures) / SUM(SUM(exposures)) OVER () * 100` for email SOV — same as ads channel. Do NOT use `AVG(individual_sov)`.

**Why:** `AVG(individual_sov)` (inbox share averaged per user) does not sum to 100% across brands because different users received different brands — there's no shared denominator. The user caught this and expected 100%-sum SOV consistent with ads.

**How to apply:** Always use the impressions-based window function for any channel SOV metric. Also: the `dtsa_mysql_read` tool does not support CTEs (`WITH` clauses) — queries must start with `SELECT` and use nested subqueries instead.
