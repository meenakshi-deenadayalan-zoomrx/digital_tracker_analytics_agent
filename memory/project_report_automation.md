---
name: Report Automation Pipeline
description: End-to-end report automation from DB to Excel (Phase 1) to PowerPoint (Phase 2) via admin portal and Claude skills
type: project
originSessionId: daaf092f-b14e-46bb-a280-ad0594af1093
---
Building a report automation pipeline: DB → Excel → PowerPoint.

**Phase 1**: Admin portal (Foal.ts) feature where users input brand/disease filters, download data for QC, upload corrections (stored in MySQL `report_corrections` table), and generate final aggregated Excel with all 5 channels and metrics.

**Phase 2**: Claude skill queries corrected data via `dtaa_report_query` MCP tool using `report_config_id`, generates PowerPoint using python-pptx with existing branded template.

**Key design decisions**:
- `report_configs` table stores filter params; `report_config_id` is the single key linking everything
- `report_corrections` table: polymorphic, simple overrides (latest wins), no audit trail
- Shared SQL templates in `sql_templates/` used by both Foal.ts and Claude MCP tools
- Corrections applied at query time via CTEs (non-destructive to source data)

**Why:** Manual report generation is slow and error-prone. Phase 1 must be designed so Phase 2 flows in without rework.

**How to apply:** All Phase 1 work (schema, queries, APIs) must be designed with Claude consumption in mind. The `report_config_id` + shared SQL templates are the bridge.
