# DTAA Critical SQL Guidelines

## Mandatory Filters (Apply to ALL queries involving users)

### 1. User Quality Filter — ALWAYS REQUIRED when user_id is involved
```sql
JOIN user_speciality_mappings usm ON <channel_table>.user_id = usm.user_id
WHERE usm.speciality_id NOT IN (28, 30)
-- 28 = Test Users, 30 = Removed Users
```

### 2. Survey Response Filter — ALWAYS REQUIRED
```sql
WHERE <channel_table>.user_wave_id IS NULL
-- user_wave_id IS NOT NULL means survey response — exclude from all analysis
```
**Exception**: posts table does not have user_wave_id; apply this filter on `web_contents` in the posts join instead.

### 3. Web Contents Type Filter — ALWAYS REQUIRED for web channel
```sql
WHERE web_contents.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
```

---

## Speciality ID Reference

| ID | Label |
|----|-------|
| 28 | Test Users |
| 29 | gMG Patients |
| 30 | Removed Users |
| 32 | Alzheimer's Patients |

**Patient filter** (when user refers to patients):
```sql
WHERE usm.speciality_id IN (29, 32)
```

---

## Date Conventions

- **Quarter mapping**: Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec
- **Always use timestamps** in BETWEEN clauses:
  ```sql
  WHERE created BETWEEN '2025-01-01 00:00:00' AND '2025-03-31 23:59:59'
  ```
- **Emails**: Always use `received_date`, never `created`
- **Posts**: Always join `web_content_posts` → `web_contents.created` for date filtering

---

## String Matching

- Use **REGEXP** (not LIKE or =) for entity name matching — supports variations
- Case-insensitive by default due to utf8mb4_0900_ai_ci collation
- Example: `WHERE LOWER(bt.standard_name) REGEXP 'opdivo|nivolumab|bms.936558'`

---

## SQL Aggregation Strategy

| Scenario | Use |
|----------|-----|
| One record can belong to only ONE category | `CASE WHEN` |
| One record can belong to MULTIPLE categories | `UNION ALL` |

**Rule**: "Can one record belong to multiple categories?" → Yes = UNION ALL, No = CASE WHEN

### LEFT JOIN Fan-out Warning

When using LEFT JOIN to a one-to-many table (e.g., `gpt_annotations_diseases`) and then doing `SUM(CASE WHEN disease = X THEN ...)` or `COUNT(*)`, the LEFT JOIN fans out one entity row into multiple rows (one per disease). Any SUM or COUNT over the entity will multiply-count it.

**Symptom**: SUM of all category buckets > total distinct entities; a category shows a higher count than seems reasonable.

**Fix**: Do NOT compute category aggregations over a LEFT JOIN'd detail table. Instead:
- Use `EXISTS` subquery to check for a condition without fanning out rows, OR
- Aggregate (deduplicate) into a subquery first, then JOIN the result

```sql
-- WRONG: fans out email rows per disease, inflating SUM
SELECT SUM(CASE WHEN dt.standard_name REGEXP 'mf' THEN 1 ELSE 0 END) AS mf_count
FROM emails e
LEFT JOIN gpt_annotations ga ON ga.entity_id = e.id AND ga.entity_type = 'EMAIL'
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
LEFT JOIN disease_terms dt ON gad.disease_id = dt.id

-- CORRECT: pre-aggregate category per email id, then count
SELECT SUM(CASE WHEN disease_category = 'MF' THEN 1 ELSE 0 END) AS mf_count
FROM (
    SELECT e.id,
           MAX(CASE WHEN LOWER(dt.standard_name) REGEXP 'mf|myelofibrosis' THEN 'MF' ELSE NULL END) AS disease_category
    FROM emails e
    LEFT JOIN gpt_annotations ga ON ga.entity_id = e.id AND ga.entity_type = 'EMAIL'
    LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
    LEFT JOIN disease_terms dt ON gad.disease_id = dt.id
    GROUP BY e.id
) categorized
```

---

## NULL Handling

- **Disease NULL = TA agnostic**: No disease tag on an entity means it's not disease-specific
- Include NULL disease annotations ONLY when user explicitly asks for "TA agnostic", "without disease filter", or "all content regardless of disease"
- Default: **exclude** TA agnostic content when a disease filter is specified
- Always `LEFT JOIN` disease tables and handle NULLs explicitly

---

## Healthcare Relevance Filtering

- Healthcare entities: `gpt_annotations.is_healthcare_relevant = 1`
- Non-healthcare entities: `gpt_annotations.is_healthcare_relevant = 0`
- When not mentioned: do not apply this filter

---

## Active Users Definition

Active users = users with at least one data point in ANY channel:
```sql
-- Active users across all channels
SELECT DISTINCT user_id FROM ads WHERE user_wave_id IS NULL
UNION
SELECT user_id FROM web_contents WHERE user_wave_id IS NULL AND type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
UNION
SELECT user_id FROM search_results
UNION
SELECT DISTINCT wc.user_id FROM web_content_posts wcp JOIN web_contents wc ON wcp.web_content_id = wc.id
UNION
SELECT DISTINCT user_id FROM emails
```

---

## Brand Combination Rule

When brands appear as combinations in DB output (e.g., "Cabometyx,Opdivo"), treat them as **single combination brands**. Do NOT split them.

---

## Privacy Rules

- `users` table: SELECT only `users.id` (as user_id) and `users.npi` (only when explicitly requested)
- All other `users` columns are FORBIDDEN in SELECT
- Use `users` only for JOIN (NPI matching) or WHERE conditions

---

## Response Format

- 2-3 bullet points with key findings (include actual numbers and %)
- Markdown table for multi-column data
- 2-3 actionable insights
- At most one follow-up question if further exploration is relevant

---

## Database-Only Rule

- NEVER use external medical/pharmaceutical knowledge to assume data values
- ALL analysis must come from database queries
- Always query first → discover → confirm → analyze
