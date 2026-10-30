---
name: digital-tracker-diagnostics
description: "Diagnose Perxcept Digital Tracker volume, data-quality, latency, and selector issues with governed DB checks. Selector checks require Playwright; code correlation requires authorized local tracker repos; Phabricator ticket creation requires a separate employee token. Those optional integrations are not installed by the central Galen package."
team: consulting
sub_team: null
owner: vijay.ganesan@zoomrx.com
tags:
  - "digital-tracker"
  - "dtsa"
  - "diagnostics"
  - "selectors"
  - "tracking-issues"
  - "phabricator"
trigger_phrases:
  - "digital tracker volume drop"
  - "tracker selector break"
  - "zero volume in digital tracker"
  - "diagnose tracking issue"
  - "digital tracker data quality issue"
  - "extension not capturing data"
version: 9
created_at: 2026-08-24
updated_at: 2026-10-11
---
# Digital Tracker Diagnostics (DTSA)

TRIGGER: Use when a Product Owner reports a Digital Tracker tracking issue — volume drop, zero volume, selector break, data quality, or latency — across the Chrome, iOS, or macOS extensions. Do NOT use for marketing analytics questions (that is digital-tracker) or general coding tasks.

Investigate Perxcept Digital Tracker issues through the L1/L2 diagnostic playbook.
When a Product Owner reports a tracking issue, route to the appropriate reference playbook.

## Routing

| Request type | Read file |
|---|---|
| Any tracking issue (volume drop, selector break, zero data) | `references/diagnostics.md` — full investigation playbook |
| Volume / data question only | `references/database.md` — direct DB query |
| Selector break investigation | `references/selectors.md` |
| Deployment / commit correlation | Use `dtsa_github_commits` + `dtsa_github_diff`; read repo `AGENT_CONTEXT.md` |
| Create ticket | `references/ticketing.md` |
| Channel → implementation/service mapping needed | `references/service_map.json` |

## SQL and optional diagnostic operations

Use `perxcept_execute_sql` on `prod-perxcept-mysql-mcp` for DB volume and data checks. Read `references/remote-sql.md` before SQL discovery/execution. Read `references/schema-live-check.md` before selecting database or selector-audit patterns; it identifies supported checks and historical templates that must not execute against the live schema. Read `references/schema-live-check.md` before selecting database or selector-audit patterns; it identifies supported checks and historical templates that must not execute against the live schema. Read `references/configuration.md` when the native connection fails or when setting up optional selector/repository/ticket operations.

The central MCP exposes SQL only. Seven historical non-SQL actions are retained through `scripts/diagnostic-actions.py`: `dtsa_playwright_selector`, `dtsa_github_commits`, `dtsa_github_diff`, `dtsa_read_file`, `dtsa_grep_repo`, `dtsa_list_repo_files`, and `dtsa_phabricator_create_task`. Run an explicit action through `galen-python` with an argument JSON file as described in configuration. They are not MCP tools supplied by the central SQL service. Optional setup is not installed automatically and does not block DB checks. Ticket creation needs an explicit concrete user request and `--allow-ticket-write`.

No new end-to-end acceptance is implied by the historical DB probe. Native MCP access, complete SQL result handling, optional selector/repository/ticket branches and affected native Windows sandbox cases must each be verified independently.

For Windows repository canonicalization errors, read `references/configuration.md` before retrying; the repository-read fallback does not repair sandbox startup.

## Repo Architecture Context
Before reading code, always load the relevant `AGENT_CONTEXT.md` first:
- `dtsa_read_file("digitrace-chrome-extension/AGENT_CONTEXT.md")`
- `dtsa_read_file("perxcept-ap-server/AGENT_CONTEXT.md")`
- `dtsa_read_file("perxcept-ios/AGENT_CONTEXT.md")`
- `dtsa_read_file("perxcept-macos/AGENT_CONTEXT.md")`
- `dtsa_read_file("perxcept-data-processing-service/AGENT_CONTEXT.md")`

Each `AGENT_CONTEXT.md` links to `docs/*.md` for deeper context.

Code investigation requires local clones of the five tracker repos (4 live on Phabricator, 1 on GitHub). If they are missing, run `scripts/clone_repos.sh` (macOS/Linux) or `scripts\clone_repos.bat` (Windows) with a target folder, then set the non-secret `DTSA_LOCAL_REPOS_BASE` environment variable.

## Tone
Evidence-first. Label every finding CONFIRMED / LIKELY / INCONCLUSIVE.
Never speculate — if evidence is absent, say so.

## Prerequisites
- Native `prod-perxcept-mysql-mcp` connection, employee Entra assignment and `perxcept_execute_sql` for DB checks. No local DB driver/helper/runtime is required.
- For optional actions only: Galen's `galen-python` command or an explicitly selected Python interpreter; authorized local repositories; Git/GitPython or optional GitHub httpx access for commit analysis; Playwright plus Chromium for live selectors; httpx and an approved Phabricator token/URL for ticket creation. These separate integrations are not centrally installed by this skill.

## Secrets
- Native client OAuth session for Perxcept; no local DB secrets.
- Optional `DTSA_GITHUB_TOKEN` and `DTSA_PHABRICATOR_API_TOKEN` are supplied through the process environment by their existing approved setup, never action JSON or chat. `DTSA_LOCAL_REPOS_BASE` and `DTSA_PHABRICATOR_API_URL` are explicit non-secret configuration.

## Health Check
- file: references/diagnostics.md

For requested connection acceptance, read `references/remote-sql.md`. For optional action setup, read `references/configuration.md`. A healthy SQL connection does not validate those integrations.
