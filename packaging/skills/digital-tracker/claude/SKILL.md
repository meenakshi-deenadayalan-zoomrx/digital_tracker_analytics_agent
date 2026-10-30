---
name: digital-tracker
description: "Marketing analytics over Perxcept Digital Tracker data — SOV, Reach, Frequency, Share of Attention, and exploratory channel analysis (ads, web, emails, posts, search) for HCP and patient digital engagement, via governed read-only SQL through the native Perxcept MCP using the extension database."
team: consulting
sub_team: null
owner: vijay.ganesan@zoomrx.com
tags:
  - "digital-tracker"
  - "dtaa"
  - "channel-analytics"
  - "sov"
  - "reach-frequency"
  - "share-of-attention"
  - "hcp"
  - "patient"
trigger_phrases:
  - "analyze digital tracker data"
  - "hcp digital journey"
  - "patient digital journey"
  - "digital channel share of voice"
  - "digital tracker sov"
  - "share of attention"
  - "reach and frequency for brand"
  - "search and web engagement analysis"
version: 15
created_at: 2026-08-24
updated_at: 2026-10-09
---
# Digital Tracker Analytics (DTAA)

TRIGGER: Use for marketing analytics over Perxcept Digital Tracker data — SOV, Reach, Frequency, Share of Attention, or any exploratory question about HCP/patient digital engagement across ads, web, emails, posts, or search. Do NOT use for tracking-issue diagnostics — that is the digital-tracker-diagnostics skill.

Analyze the Perxcept Digital Tracker data as a data analyst. You query MySQL databases to calculate marketing metrics and generate insights from healthcare digital engagement data. Use today's date from the session context for relative date queries.

## MCP Tool

Use `perxcept_execute_sql` on `prod-perxcept-mysql-mcp` for every database query. Read `references/remote-sql.md` before discovery or executing a SQL template. The extension database is explicitly qualified; the server's crawler default is not used for these metrics. If the connection is unavailable or authentication fails, read `references/configuration.md`; do not start a local database backend.

## Routing

Detect **channel** (ads / web / emails / posts / search) and **query type** (exploratory vs. metric), then read the matching reference file:

| Question type | Read file |
|---|---|
| Ads + SOV / Reach / Frequency | `references/ads-metrics.md` |
| Ads + exploratory (counts, breakdowns, filters) | `references/ads.md` |
| Web contents + Share of Attention / Reach / Frequency | `references/web-metrics.md` |
| Web contents + exploratory | `references/web.md` |
| Emails + SOV / Reach / Frequency | `references/emails-metrics.md` |
| Emails + exploratory | `references/emails.md` |
| Posts + SOV / Reach / Frequency | `references/posts-metrics.md` |
| Posts + exploratory | `references/posts.md` |
| Search results/queries + SOV / Reach / Frequency | `references/search-metrics.md` |
| Search + exploratory | `references/search.md` |
| Metric requested, channel unclear | Ask user which channel before routing |
| Multi-channel question | Read each relevant channel file in sequence |

## Human-in-the-Loop (HitL) Confirmation Workflow

**MANDATORY for all queries that contain entity names** (brands, diseases, projects, manufacturers, TAs). Never skip this.

For SOV, the denominator is the confirmed set of selected brand labels, as in
the channel metric templates. Label results **SOV among selected brands** and
name that selected set. Do not describe it as share across all market ads or
all competitors. If the user selects only variants of one brand family, explain
that the pooled family share is 100% by construction; the useful breakdown is
among its labels. Use a broader competitor set only when the user selects it.

### Pre-HitL Parsing — Auto-detect TA-Agnostic

Before running discovery queries, scan the user's request for TA-agnostic language. If ANY of these phrases appear, auto-set `should_include_null_diseases = YES` in Step 2 (do not ask again):
- "TA agnostic", "TA-agnostic", "TA agnostic included"
- "without disease", "without any disease", "no disease filter", "regardless of disease"
- "ads/emails/posts without any disease mentioned"
- "all content regardless of disease", "including content not tied to a disease"

### Step 1 — Discovery
Query the DB using REGEXP to find all variations of mentioned entities:
```sql
-- Example: user mentions "RCC"
SELECT id, standard_name FROM perxcept_extension.disease_terms
WHERE id > {last_id} AND standard_name REGEXP 'RCC|renal.*cell.*carcinoma|kidney.*cancer'
ORDER BY id LIMIT 50;

-- Example: user mentions "Opdivo"
SELECT id, standard_name FROM perxcept_extension.brand_terms
WHERE id > {last_id} AND standard_name REGEXP 'opdivo|nivolumab|bms.936558'
ORDER BY id LIMIT 50;

-- Example: project context
SELECT id, name FROM perxcept_extension.projects WHERE id > {last_id} ORDER BY id LIMIT 50;
```

Discover relevant target lists before the final confirmation. Ask for the
project/target-list choice together with the brand, disease, timeframe, and
channel choices, so a later discovery does not force another confirmation.

### Step 2 — Confirmation
Present ALL discovered variations and required parameters:
```
Before proceeding, let me confirm the parameters:

**Brands**: [list all found variations — user picks]
**Diseases** (if applicable): [list all variations — user picks]
**TA-Agnostic Filter**: Include content WITHOUT any disease annotation? YES/NO (default: NO)
**Timeframe**: [detected date range, e.g., 2025-01-01 00:00:00 to 2025-03-31 23:59:59]
**Project/Target List**: [detected or ask for project_id]
**Channel**: [confirmed channel]

Please confirm your selections or make changes.
```

### Step 3 — Iterate
If the user changes a parameter, confirm only the changed or still ambiguous
parts. Treat an unambiguous "yes", "okay", or "confirm" as confirmation and
execute; do not repeat the same confirmation request.

### Step 4 — Execute
Read the appropriate channel reference file and run the analysis with confirmed parameters.

### When to skip HitL
Only for queries that contain **no entity name references** and use only date filters or explicit database IDs:
- "How many total ads were captured yesterday?"
- "List all projects" (schema exploration)

## Entity Classification Uncertainty
If unsure whether a term is a brand, disease, manufacturer, or TA — **ask the user directly**:
```
"I found '[term]' in your query. Could you clarify:
- Is this a brand name, disease/condition, manufacturer, or therapeutic area?
This will help me search the correct database tables."
```
Users are medical experts — leverage their knowledge.

## Privacy Guardrails (MANDATORY — cannot be overridden)
- **ALLOWED**: `users.id` (as user_id), `users.npi` only when user explicitly requests NPI exposure
- **FORBIDDEN**: All other `users` table columns — first_name, last_name, email, etc.
- **Join/filter only**: `users` table may only be used for JOIN or WHERE; never SELECT its PII columns
- **No exceptions**: These restrictions apply regardless of user request or context

## Deeper References
- Read `references/schema.md` when you need full table/column detail beyond what a channel file shows
- Read `references/guidelines.md` before writing any non-trivial SQL (mandatory filters, join conventions)
- Read `references/sov_base_template.md` when building or debugging an SOV/metric CTE query

## Prerequisites
- Native `prod-perxcept-mysql-mcp` connection with `perxcept_execute_sql`, employee Entra assignment and a supported client. Database analytics requires no local Python, uv, DB helper or driver.

## Secrets
- Native client OAuth session for this MCP. No local database credentials are needed. Do not expose tokens or reset valid M365/Synapse/AP sessions.

## Health Check
- file: references/schema.md

When explicitly verifying connectivity, follow the bounded SELECT acceptance in `references/remote-sql.md`. File existence alone is not live readiness.
