# dtaa-agent

Digital Tracker **Analytics** Agent — marketing analytics over HCP/patient digital
engagement: Share of Voice, Reach, Frequency, Share of Attention, and exploratory
analysis across the ads, web, emails, posts, and search channels.

This is the repo that gets shared with teammates. Keep it clean.

## Scope boundary

| Belongs here | Goes elsewhere |
|---|---|
| `skills/dtaa*` — 13 analytics skills | Tracking-issue diagnostics → `../dtsa-agent` |
| MCP server code | Everything an analysis produces → `../analysis/<name>/` |
| Schema and query references | Dashboard monitoring → `../../AG_Jupyter_Dashboards` |

**Never write analysis outputs into this repo.** Spreadsheets, HTML artifacts,
results write-ups, PRDs — all of it goes to `../analysis/`, one folder per
analysis. `.gitignore` blocks `*.xlsx`, `*.html`, `*.csv`, and `*.sql` here as a
backstop, but the rule is the point, not the backstop.

Before writing artifacts anywhere, ask whether to keep them and in which analysis
folder — see `~/.claude/CLAUDE.md`.

## Durable knowledge belongs in the repo, not in memory

Claude Code memory is per-machine and does **not** survive a `git clone`. When a
session establishes something durable — a schema quirk, a join path, a query
constraint, a brand-normalization rule — write it into
`skills/dtaa/references/schema.md` or the relevant skill, not only into memory.
A teammate cloning this repo inherits the references and nothing else.

## Duplicated server code — must stay in sync

The 12 server files below are byte-identical copies shared with `../dtsa-agent`.
Each repo is self-contained, with its own `.venv` and `.env`.

```
config.py  dtsa_database.py  mysql_service.py
synapse_database.py  synapse_mysql_service.py  filesystem_service.py
github_service.py  phabricator_service.py  playwright_service.py
pyproject.toml  requirements.txt  .env.example
```

**Any edit to these must be mirrored to `../dtsa-agent` in the same sitting.**
`bash sync-server.sh` copies them across; `bash sync-server.sh --check` reports
drift. Commit in both repos.

**`mcp_server.py` is the exception — it is intentionally different, never synced.**
Here it is a lean server for the consulting audience: two read-only SQL tools
(`dtsa_mysql_read`, `synapse_mysql_read`) and nothing else, with service modules
imported lazily so startup stays fast. `../dtsa-agent` keeps the full 9-tool
server (GitHub, Phabricator, Playwright, filesystem). Edit each on its own; do not
copy one over the other. This server only imports `mysql_service.py` and
`synapse_mysql_service.py` (and their database/config modules), so changes to
those shared files still affect it. `github_service.py`, `phabricator_service.py`,
`playwright_service.py` and `filesystem_service.py` are unused here and stay only
to keep the shared set identical.

`mcp` is pinned to `>=1.26,<2` — 2.0.0 removed `Server.list_tools`, which
`mcp_server.py` registers its tools through. Do not relax that pin without
migrating the server to the 2.0 API.

## Naming

Variables and tools keep the `DTSA_` / `dtsa_` prefix (`dtsa_mysql_read`,
`DTSA_EXTENSION_DB_READ_HOST`) because both agents share one server codebase.
This is historical, not meaningful — nothing about those tools is specific to the
support agent. The MCP namespace is what distinguishes them: `mcp__dtaa__` here,
`mcp__dtsa__` in the sibling repo.

## Skills

`dtaa` routes everything. Channel skills come in pairs — `dtaa-<channel>` for
exploratory work, `dtaa-<channel>-metrics` for SOV/Reach/Frequency. Plus
`dtaa-chat-extractor` (MedAI conversations from the DB) and `dtaa-chat-parser`
(from a supplied Excel/CSV).

Install with `cp -r skills/dtaa* ~/.claude/skills/`. See `SETUP.md`.
