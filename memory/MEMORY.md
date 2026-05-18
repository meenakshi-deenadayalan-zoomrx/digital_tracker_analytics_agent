# DTSA MCP Server — Project Memory

## Project Overview
MCP server for Digital Tracker agents (DTSA + DTAA). Located at `C:\Users\MeenakshiDeenadayala\Documents\dtsa-mcp-server\dtsa-mcp-server`.

## Two Agent Systems

### DTSA (Digital Tracker Support Agent)
- **Purpose**: Diagnosing tracking issues (volume drops, selector breaks)
- **Skills**: `dtsa`, `dtsa-database`, `dtsa-diagnostics`, `dtsa-selectors`, `dtsa-ticketing`
- **MCP Tools**: All 8 tools (mysql, playwright, github, phabricator, filesystem)

### DTAA (Digital Tracker Analytics Agent)
- **Purpose**: Marketing analytics (SOV, Reach, Frequency, Share of Attention)
- **Created**: March 2026
- **Skills**: 11 skill directories, 19 files total
- **MCP Tools**: `dtsa_mysql_read` only (no new Python code needed)
- **Skill structure**: See `dtaa-architecture.md`

## DTAA Skill Structure
```
skills/dtaa/                    → orchestrator (HitL, routing, privacy)
skills/dtaa/references/         → schema.md, guidelines.md, sov_base_template.md
skills/dtaa-ads/ + dtaa-ads-metrics/
skills/dtaa-web/ + dtaa-web-metrics/
skills/dtaa-emails/ + dtaa-emails-metrics/
skills/dtaa-posts/ + dtaa-posts-metrics/
skills/dtaa-search/ + dtaa-search-metrics/
```

## Key Architecture Decisions
- Channel skills split: `dtaa-<channel>` (exploratory) + `dtaa-<channel>-metrics` (SOV/Reach/Frequency)
- Web channel uses **Share of Attention** (weighted duration), not SOV
- SOV base template in `dtaa/references/sov_base_template.md` — all metric skills reference it
- Scalability: add channel → create 2 dirs + update orchestrator routing table

## Install Skills
```bash
cp -r skills/dtaa* ~/.claude/skills/
```

## MCP Server Entry Point
`mcp_server.py` — stdio transport, 8 tools, uses service classes

## Tool Usage
- [DTAA tool namespace](feedback_dtaa_tool_namespace.md) — Use `mcp__dtsa__dtsa_mysql_read` for DTAA analytics, NOT `mcp__dtsa-tools__dtsa_mysql_read`

## Query Constraints & Bug Fixes
- [Email SOV formula](feedback_email_sov_formula.md) — Use window function for SOV (not AVG inbox share); no CTEs in dtsa_mysql_read
- [Web SoA correct weight join](feedback_web_soa_no_weight_table.md) — use `gpt_annotations_disease_brand_weights` (not `gpt_annotations_diseases_brands`); join brand_terms + disease_terms via brand_id/disease_id; multiply duration × weight
- [Inline literals for REGEXP](feedback_inline_literals_regexp.md) — %(param)s fails inside CASE WHEN REGEXP; always hardcode regex patterns as literals

## Active Projects
- [Report Automation Pipeline](project_report_automation.md) — DB→Excel→PPT automation, Phase 1 (admin portal) then Phase 2 (Claude PPT)
- [DT Reporting Agent PRD](project_dt_reporting_agent.md) — AI agent for full DT report generation, PRD in progress
