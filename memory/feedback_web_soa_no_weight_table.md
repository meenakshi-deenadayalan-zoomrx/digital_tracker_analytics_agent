---
name: Web SoA — correct weight join table
description: Use gpt_annotations_disease_brand_weights (not gpt_annotations_diseases_brands) for web SoA brand-disease-level weights
type: feedback
originSessionId: 00f415b2-6687-4af7-9355-f3c71eb7b158
---
The `dtaa-web-metrics` skill template references `gpt_annotations_diseases_brands` (does not exist) and `gpt_annotations_brands` (exists but has 0 brand annotations for WEB_CONTENT_GROUP entity type). The correct table is `gpt_annotations_disease_brand_weights`.

**Why:** For WEB_CONTENT_GROUP annotations, brand + disease + weight data is all stored in `gpt_annotations_disease_brand_weights` (brand_id, disease_id, weight columns). The `gpt_annotations_brands` table is populated for other entity types (ADs, etc.) but not for web content groups.

**How to apply:** In all web Share of Attention queries, replace the separate `gpt_annotations_brands` + `gpt_annotations_diseases` joins with a single join to `gpt_annotations_disease_brand_weights gadbw`. Then:
- `JOIN gpt_annotations_disease_brand_weights gadbw ON gadbw.gpt_annotation_id = ga.id`
- `JOIN brand_terms bt ON gadbw.brand_id = bt.id`
- `JOIN disease_terms dt ON gadbw.disease_id = dt.id` (use JOIN not LEFT JOIN when disease filter is required)
- Use `SUM(TIME_TO_SEC(wc.duration) * COALESCE(gadbw.weight, 1))` as brand_seconds
- For TA-agnostic (include null disease): `LEFT JOIN disease_terms dt ... AND (LOWER(dt.standard_name) REGEXP '...' OR gadbw.disease_id IS NULL)`

Do NOT join `gpt_annotations_brands` or `gpt_annotations_diseases` separately for web contents.
