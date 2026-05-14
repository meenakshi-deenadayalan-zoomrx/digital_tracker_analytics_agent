# Project Mode — SQL Reference

This document contains all SQL patterns for Project Mode. Channel metric skills reference this instead of building their own filter logic.

---

## Step 1 — Resolve Project ID

```sql
SELECT id, name FROM projects WHERE name = '{project_name}';
-- If not found, try partial match:
SELECT id, name FROM projects WHERE name REGEXP '{keyword}' ORDER BY name;
```

---

## Step 2 — Load Report Filters

Fetch brands (UNION ALL across all filter records for this project):

```sql
SELECT DISTINCT rfb.brand_id, bt.standard_name AS brand_name
FROM report_filters rf
JOIN report_filters_brands rfb ON rfb.filter_id = rf.id
JOIN brand_terms bt ON bt.id = rfb.brand_id
WHERE rf.project_id = {project_id}
ORDER BY brand_name;
```

Fetch disease/indication filter spec (UNION ALL across all filter records):

```sql
SELECT DISTINCT
    rfid.disease_id,
    d.name AS disease_name,
    rfid.indication_id,
    i.standard_name AS indication_name
FROM report_filters rf
JOIN report_filters_indications_diseases rfid ON rfid.filter_id = rf.id
JOIN diseases d ON d.id = rfid.disease_id
LEFT JOIN indications i ON i.id = rfid.indication_id
WHERE rf.project_id = {project_id}
ORDER BY disease_name, indication_name;
```

From these results, build two lists:
- `{disease_only_ids}` — disease_id values where indication_id IS NULL
- `{specific_indication_ids}` — indication_id values where indication_id IS NOT NULL

---

## Step 3 — Build Disease/Indication Filter

Based on what's in `report_filters_indications_diseases`:

### Case A — Disease-level only (indication_id is NULL for all rows)
```sql
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
-- Filter: AND gad.disease_id IN (11347, 5821, ...)
```

### Case B — Indication-level only (all rows have indication_id)
```sql
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
-- Filter: AND gad.indication_id IN (125512, 125513, ...)
```

### Case C — Mixed (some disease-level, some indication-specific)
```sql
LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
-- Filter:
-- AND (
--     gad.disease_id IN ({disease_only_ids})        -- broad: any indication under this disease
--     OR gad.indication_id IN ({specific_indication_ids})  -- specific indications
-- )
```

**Rule**: If a filter row has only `disease_id` → match any `gad.disease_id` equal to it (covers all indications under that disease). If a filter row has both `disease_id` + `indication_id` → match only `gad.indication_id` equal to it.

---

## Step 4 — Apply QC Overrides

QC overrides replace annotation assignments at the per-annotation level. Apply whenever `project_id` is known.

### Brand QC Override
Replace the standard `gpt_annotations_brands` join with:
```sql
-- Instead of: JOIN gpt_annotations_brands gab ON ga.id = gab.gpt_annotation_id
-- Use:
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

### Disease/Indication QC Override
Replace the standard `gpt_annotations_diseases` join with:
```sql
-- Instead of: LEFT JOIN gpt_annotations_diseases gad ON ga.id = gad.gpt_annotation_id
-- Use:
LEFT JOIN (
    SELECT gad.gpt_annotation_id,
           COALESCE(rqid.disease_id, gad.disease_id)         AS disease_id,
           COALESCE(rqid.indication_id, gad.indication_id)   AS indication_id
    FROM gpt_annotations_diseases gad
    LEFT JOIN report_qc_indications_diseases rqid
        ON rqid.gpt_annotations_id = gad.gpt_annotation_id
        AND rqid.project_id = {project_id}
) gad ON ga.id = gad.gpt_annotation_id
```

### Web Channel — SoA Weight Join with QC Disease Override
For `gpt_annotations_disease_brand_weights` (web SoA only), apply disease QC before the weight join:
```sql
LEFT JOIN gpt_annotations_disease_brand_weights gadb
    ON ga.id = gadb.gpt_annotation_id
    AND gadb.brand_id = gab.brand_id
    AND gadb.disease_id = gad.disease_id       -- gad.disease_id is already QC-overridden
    AND (gadb.indication_id = gad.indication_id OR gad.indication_id IS NULL)
```

---

## Step 5 — Brand Filter (Project Mode)

In Project Mode, use `brand_id IN (...)` instead of the REGEXP text pattern.
No `{brand_normalization}` CASE expression is needed — `bt.standard_name` is the display name directly.

```sql
-- Replace: AND LOWER(bt.standard_name) REGEXP '{brand_regex}'
-- With:    AND gab.brand_id IN ({brand_ids})
-- e.g.:   AND gab.brand_id IN (53, 63, 200)
```

In the `GROUP_CONCAT` inside SOV queries, simplify from:
```sql
GROUP_CONCAT(DISTINCT CASE {brand_normalization} ELSE bt.standard_name END) AS brand_name
-- To:
GROUP_CONCAT(DISTINCT bt.standard_name) AS brand_name
```

---

## QC Tables Reference

| Table | Overrides | Key columns |
|---|---|---|
| `report_qc_brands` | brand assignment per annotation | `project_id, gpt_annotations_id, brand_id` |
| `report_qc_indications_diseases` | disease/indication per annotation | `project_id, gpt_annotations_id, disease_id, indication_id` |
| `report_qc_manufacturers` | manufacturer per annotation | `project_id, gpt_annotations_id, manufacturer_id` |
| `report_qc_search_queries` | `is_branded` flag | `project_id, search_query_id, is_branded` |
| `report_qc_topics` | primary/secondary topic | `project_id, gpt_annotations_id, primary_topic, secondary_topic` |
| `report_qc_trial_names` | trial name per annotation | `project_id, gpt_annotations_id, trial_name_id` |
| `report_qc_web_contents` | web page type | `project_id, webcontent_id, llm_web_page_type` |
| `report_qc_email_senders` | sender category | `project_id, email_id, sender_category` |
