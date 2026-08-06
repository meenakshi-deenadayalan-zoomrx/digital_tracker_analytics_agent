# DTAA — Setup Guide

Sets up the **Digital Tracker Analytics Agent** in Claude Desktop: 13 analytics
skills plus the MCP server that queries the Digital Tracker databases.

No programming experience required. Follow each step in order.

Jump to your OS: [macOS](#macos) · [Windows](#windows) · [Linux](#linux)

> Looking for tracking-issue diagnostics (volume drops, selector breaks)? That is
> a separate agent — see the `dtsa-agent` repo.

---

## What you need before starting

- **Claude Desktop** — [claude.ai/download](https://claude.ai/download)
- **Python 3.10 or later**
- **git** — [git-scm.com](https://git-scm.com/downloads)
- A **credentials sheet** from your team: extension DB and Synapse DB host,
  username, password

Estimated time: **10–15 minutes**

---

## macOS

### Step 1 — Clone the repository

Open **Terminal** (`Cmd+Space` → type `Terminal` → Enter):

```
git clone https://github.com/meenakshi-deenadayalan-zoomrx/digital_tracker_analytics_agent.git ~/Desktop/dtaa-agent
```

Any permanent location works. Get the full path with:

```
cd ~/Desktop/dtaa-agent && pwd
```

Example result: `/Users/jane/Desktop/dtaa-agent`. Use it wherever this guide says
`/path/to/dtaa-agent`.

### Step 2 — Check Python

```
python3 --version
```

`3.10` or higher is fine. Otherwise install from
[python.org/downloads](https://www.python.org/downloads/).

### Step 3 — Install dependencies

```
cd /path/to/dtaa-agent
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Takes 1–2 minutes. You do **not** need `playwright install chromium` — that is
only for the selector-testing tool, which DTAA does not use.

### Step 4 — Add credentials

```
cp /path/to/dtaa-agent/.env.example /path/to/dtaa-agent/.env
```

Open `.env` (right-click → Open With → TextEdit) and fill in:

```
DTSA_EXTENSION_DB_READ_HOST=       ← Digital Tracker DB address
DTSA_EXTENSION_DB_READ_USERNAME=
DTSA_EXTENSION_DB_READ_PASSWORD=

SYNAPSE_DB_HOST=                   ← community-data.zoomrx.com
SYNAPSE_DB_USERNAME=
SYNAPSE_DB_PASSWORD=
```

Leave the Phabricator and GitHub entries blank — DTAA does not use them.

### Step 5 — Install skills

```
mkdir -p ~/.claude/skills
cp -r /path/to/dtaa-agent/skills/dtaa* ~/.claude/skills/
```

Verify with `ls ~/.claude/skills/` — you should see 13 entries:

```
dtaa  dtaa-ads  dtaa-ads-metrics  dtaa-chat-extractor  dtaa-chat-parser
dtaa-emails  dtaa-emails-metrics  dtaa-posts  dtaa-posts-metrics
dtaa-search  dtaa-search-metrics  dtaa-web  dtaa-web-metrics
```

### Step 6 — Configure Claude Desktop

```
open -a TextEdit ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Add inside `"mcpServers": {`:

```json
"dtaa": {
  "command": "/path/to/dtaa-agent/.venv/bin/python",
  "args": ["/path/to/dtaa-agent/mcp_server.py"],
  "env": {
    "PYTHONPATH": "/path/to/dtaa-agent"
  }
}
```

Example for `/Users/jane/Desktop/dtaa-agent`:

```json
"dtaa": {
  "command": "/Users/jane/Desktop/dtaa-agent/.venv/bin/python",
  "args": ["/Users/jane/Desktop/dtaa-agent/mcp_server.py"],
  "env": {
    "PYTHONPATH": "/Users/jane/Desktop/dtaa-agent"
  }
}
```

### Step 7 — Verify

1. Quit Claude Desktop fully (menu bar icon → Quit), then reopen.
2. New conversation → `What tools do you have available?` → you should see 9,
   including `dtsa_mysql_read` and `synapse_mysql_read`.
3. Type `/dtaa` — the analytics orchestrator should activate.
4. Ask something small, e.g. *"How many web content records were captured last
   week?"*

---

## Windows

### Step 1 — Clone the repository

Open **Command Prompt** (`Win+R` → `cmd` → Enter):

```
git clone https://github.com/meenakshi-deenadayalan-zoomrx/digital_tracker_analytics_agent.git C:\Tools\dtaa-agent
```

Avoid folder names with spaces.

### Step 2 — Check Python

```
python --version
```

If installing fresh, **check "Add Python to PATH"** during setup.

### Step 3 — Install dependencies

```
cd C:\Tools\dtaa-agent
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### Step 4 — Add credentials

Copy `.env.example` to `.env`, open it in Notepad, and fill in the same fields
listed in macOS Step 4.

### Step 5 — Install skills

```
mkdir %USERPROFILE%\.claude\skills
xcopy /E /I C:\Tools\dtaa-agent\skills\dtaa* %USERPROFILE%\.claude\skills\
```

### Step 6 — Configure Claude Desktop

```
notepad "%APPDATA%\Claude\claude_desktop_config.json"
```

Add inside `"mcpServers": {` — **double every backslash**:

```json
"dtaa": {
  "command": "C:\\Tools\\dtaa-agent\\.venv\\Scripts\\python.exe",
  "args": ["C:\\Tools\\dtaa-agent\\mcp_server.py"],
  "env": {
    "PYTHONPATH": "C:\\Tools\\dtaa-agent"
  }
}
```

### Step 7 — Verify

Same as macOS Step 7.

---

## Linux

### Step 1 — Clone the repository

```bash
git clone https://github.com/meenakshi-deenadayalan-zoomrx/digital_tracker_analytics_agent.git ~/tools/dtaa-agent
```

### Step 2 — Check Python

```bash
python3 --version
# Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv
# Fedora/RHEL:   sudo dnf install python3 python3-pip
```

### Step 3 — Install dependencies

```bash
cd /path/to/dtaa-agent
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Step 4 — Add credentials

```bash
cp .env.example .env
nano .env
```

Fill in the same fields listed in macOS Step 4.

### Step 5 — Install skills

```bash
mkdir -p ~/.claude/skills
cp -r /path/to/dtaa-agent/skills/dtaa* ~/.claude/skills/
```

### Step 6 — Configure Claude Desktop

Config file: `~/.config/Claude/claude_desktop_config.json`

```json
"dtaa": {
  "command": "/path/to/dtaa-agent/.venv/bin/python",
  "args": ["/path/to/dtaa-agent/mcp_server.py"],
  "env": {
    "PYTHONPATH": "/path/to/dtaa-agent"
  }
}
```

### Step 7 — Verify

Same as macOS Step 7.

---

## What the skills do

| Skill | Use for |
|---|---|
| `dtaa` | Orchestrator — routes to the right channel skill |
| `dtaa-ads` / `dtaa-ads-metrics` | Ads: breakdowns / SOV, Reach, Frequency |
| `dtaa-web` / `dtaa-web-metrics` | Web: page visits / Share of Attention |
| `dtaa-emails` / `dtaa-emails-metrics` | Emails: senders, subjects / SOV |
| `dtaa-posts` / `dtaa-posts-metrics` | Sponsored posts (FB, LinkedIn, YouTube) |
| `dtaa-search` / `dtaa-search-metrics` | Search ads, organic, AI references |
| `dtaa-chat-extractor` | MedAI conversations pulled from the database |
| `dtaa-chat-parser` | MedAI conversations from a supplied Excel/CSV |

Start with `/dtaa` and let it route — you rarely need to name a channel skill
directly.

---

## Credentials reference

| Variable | What it is | Required |
|---|---|---|
| `DTSA_EXTENSION_DB_READ_HOST` | Digital Tracker DB hostname | Yes |
| `DTSA_EXTENSION_DB_READ_USERNAME` | DB username | Yes |
| `DTSA_EXTENSION_DB_READ_PASSWORD` | DB password | Yes |
| `SYNAPSE_DB_HOST` | Synapse DB (`community-data.zoomrx.com`) | For community data |
| `SYNAPSE_DB_USERNAME` / `SYNAPSE_DB_PASSWORD` | Synapse credentials | For community data |
| `DTSA_PHABRICATOR_*`, `DTSA_GITHUB_TOKEN`, `DTSA_LOCAL_REPOS_BASE` | Used by the DTSA support agent | No — leave blank |

The variables keep their `DTSA_` prefix because both agents share one server
codebase. Nothing about them is DTSA-specific in practice.

---

## Troubleshooting

**No tools listed in Claude Desktop**
- Check `.env` exists and is filled in
- Check `claude_desktop_config.json` is valid JSON (no trailing commas)
- Windows: every backslash must be doubled (`\\`)

**`AttributeError: 'Server' object has no attribute 'list_tools'`**
- Your `mcp` package is 2.x. The server needs the 1.x line. Fix with:
  `.venv/bin/pip install "mcp>=1.26,<2"` (Windows: `.venv\Scripts\pip`)

**`No module named 'config'`**
- `PYTHONPATH` must point at the `dtaa-agent` folder itself

**Connection error on a query**
- DB credentials in `.env` are wrong — re-check with your team

**`/dtaa` not recognized**
- Skills must be in `~/.claude/skills/` (`%USERPROFILE%\.claude\skills\` on
  Windows), each folder containing a `SKILL.md`

**Test the server by hand:**

```bash
/path/to/dtaa-agent/.venv/bin/python /path/to/dtaa-agent/mcp_server.py
```

It will sit waiting for input — that means it started cleanly. Press `Ctrl+C` to
exit. Any traceback printed instead is the real error; share it with your team.

---

## Keeping it updated

```bash
cd /path/to/dtaa-agent
git pull
```

After pulling:
1. Re-run Step 3 if `requirements.txt` changed
2. Re-run Step 5 to refresh `~/.claude/skills/`
3. Restart Claude Desktop

Your `.env` is yours — `git pull` never overwrites it.
