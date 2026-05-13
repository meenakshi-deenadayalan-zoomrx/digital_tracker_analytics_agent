# DTSA MCP Server — Setup Guide

This sets up the DTSA diagnostic agent tools in Claude Desktop.
No programming experience required. Follow each step in order.

Jump to your OS:
- [macOS](#macos)
- [Windows](#windows)
- [Linux](#linux)
- [Getting the repositories](#getting-the-repositories)

---

## What you need before starting

- **Claude Desktop** installed — [claude.ai/download](https://claude.ai/download)
- The `dtsa-mcp-server` folder (the zip you received from your team)
- Your **credentials sheet** from your team:
  - DB host, username, password
  - Phabricator API token and URL
- Access to clone the 5 ZoomRx repositories (see [Getting the repositories](#getting-the-repositories))

Estimated time: **20–30 minutes** (including repo cloning)

---

## macOS

### Step 1 — Place the folder

1. Double-click the zip to unzip it
2. Move `dtsa-mcp-server` somewhere permanent (Desktop or Documents)
   - Do **not** leave it in Downloads — it may get deleted
3. Find your full path — right-click → **Get Info** → look at **Where**
   - Example: `/Users/jane/Desktop/dtsa-mcp-server`

### Step 2 — Install Python 3.10 or later

Open **Terminal** (`Cmd+Space` → type `Terminal` → Enter):

```
python3 --version
```

If it prints `3.10` or higher, skip to Step 3.
Otherwise install from [python.org/downloads](https://www.python.org/downloads/).

### Step 3 — Install dependencies

Replace `/path/to/dtsa-mcp-server` with your actual path from Step 1:

```
cd /path/to/dtsa-mcp-server
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

Each command may take 1–2 minutes. Wait for each to finish.

### Step 4 — Add credentials

1. Copy the example config:
   ```
   cp /path/to/dtsa-mcp-server/.env.example /path/to/dtsa-mcp-server/.env
   ```
2. Open `.env` in TextEdit: right-click → Open With → TextEdit
3. Fill in your values (get these from your team's credentials sheet):

   ```
   DTSA_EXTENSION_DB_READ_HOST=       ← DB server address
   DTSA_EXTENSION_DB_READ_USERNAME=   ← DB username
   DTSA_EXTENSION_DB_READ_PASSWORD=   ← DB password

   DTSA_PHABRICATOR_API_TOKEN=        ← Phabricator API token
   DTSA_PHABRICATOR_API_URL=          ← e.g. https://phabricator.company.com
   ```

   For code investigation — clone the repos first (see [Getting the repositories](#getting-the-repositories)), then set:
   ```
   DTSA_LOCAL_REPOS_BASE=/path/to/zoomrx-repos
   ```
   *(Local clones are strongly recommended — 4 of 5 repos are on Phabricator, not GitHub)*

4. Save and close

### Step 5 — Install skills

```
mkdir -p ~/.claude/skills
cp -r /path/to/dtsa-mcp-server/skills/dtsa* ~/.claude/skills/
```

Verify:
```
ls ~/.claude/skills/
```
You should see: `dtsa  dtsa-database  dtsa-diagnostics  dtsa-selectors  dtsa-ticketing`

### Step 6 — Configure Claude Desktop

1. Open the config file:
   ```
   open -a TextEdit ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```
2. Add this block inside `"mcpServers": {`:
   ```json
   "dtsa-tools": {
     "command": "/path/to/dtsa-mcp-server/.venv/bin/python",
     "args": ["/path/to/dtsa-mcp-server/mcp_server.py"],
     "env": {
       "PYTHONPATH": "/path/to/dtsa-mcp-server"
     }
   }
   ```
   Example (folder at `/Users/jane/Desktop/dtsa-mcp-server`):
   ```json
   "dtsa-tools": {
     "command": "/Users/jane/Desktop/dtsa-mcp-server/.venv/bin/python",
     "args": ["/Users/jane/Desktop/dtsa-mcp-server/mcp_server.py"],
     "env": {
       "PYTHONPATH": "/Users/jane/Desktop/dtsa-mcp-server"
     }
   }
   ```
3. Save the file

### Step 7 — Verify

1. Quit Claude Desktop fully (Claude icon in menu bar → Quit) then reopen
2. Start a new conversation and type: `What diagnostic tools do you have available?`
3. You should see 8 tools listed
4. Type `/dtsa` — the DTSA orchestrator skill should activate

---

## Windows

### Step 1 — Place the folder

1. Right-click the zip → **Extract All**
2. Move `dtsa-mcp-server` somewhere permanent, e.g. `C:\Tools\dtsa-mcp-server`
   - Avoid folder names with spaces

### Step 2 — Install Python 3.10 or later

Open **Command Prompt** (`Win+R` → type `cmd` → Enter):

```
python --version
```

If it prints `3.10` or higher, skip to Step 3.
Otherwise install from [python.org/downloads](https://www.python.org/downloads/).
During install, **check "Add Python to PATH"**.

### Step 3 — Install dependencies

```
cd C:\path\to\dtsa-mcp-server
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m playwright install chromium
```

### Step 4 — Add credentials

1. In the folder, find `.env.example`. Copy it and rename to `.env`
2. Open `.env` in Notepad: right-click → Open with → Notepad
3. Fill in your values (same fields as macOS Step 4 above)
4. Save and close

### Step 5 — Install skills

```
mkdir %USERPROFILE%\.claude\skills
xcopy /E /I C:\path\to\dtsa-mcp-server\skills\dtsa* %USERPROFILE%\.claude\skills\
```

### Step 6 — Configure Claude Desktop

Open the config file:
```
notepad "%APPDATA%\Claude\claude_desktop_config.json"
```

Add inside `"mcpServers": {` — use **double backslashes** in every path:
```json
"dtsa-tools": {
  "command": "C:\\path\\to\\dtsa-mcp-server\\.venv\\Scripts\\python.exe",
  "args": ["C:\\path\\to\\dtsa-mcp-server\\mcp_server.py"],
  "env": {
    "PYTHONPATH": "C:\\path\\to\\dtsa-mcp-server"
  }
}
```

Example (folder at `C:\Tools\dtsa-mcp-server`):
```json
"dtsa-tools": {
  "command": "C:\\Tools\\dtsa-mcp-server\\.venv\\Scripts\\python.exe",
  "args": ["C:\\Tools\\dtsa-mcp-server\\mcp_server.py"],
  "env": {
    "PYTHONPATH": "C:\\Tools\\dtsa-mcp-server"
  }
}
```

### Step 7 — Verify

Same as macOS Step 7.

---

## Linux

### Step 1 — Place the folder

```bash
unzip dtsa-mcp-server.zip -d ~/tools/
```

### Step 2 — Install Python 3.10 or later

```bash
python3 --version
```

If below 3.10:
```bash
# Ubuntu / Debian
sudo apt install python3 python3-pip python3-venv

# Fedora / RHEL
sudo dnf install python3 python3-pip
```

### Step 3 — Install dependencies

```bash
cd /path/to/dtsa-mcp-server
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python -m playwright install-deps chromium   # Linux only
```

### Step 4 — Add credentials

```bash
cp .env.example .env
nano .env   # or any text editor
```

Fill in your values (same fields as macOS Step 4), save and exit.

### Step 5 — Install skills

```bash
mkdir -p ~/.claude/skills
cp -r /path/to/dtsa-mcp-server/skills/dtsa* ~/.claude/skills/
```

### Step 6 — Configure Claude Desktop

Config file: `~/.config/Claude/claude_desktop_config.json`

```bash
nano ~/.config/Claude/claude_desktop_config.json
```

Add inside `"mcpServers": {`:
```json
"dtsa-tools": {
  "command": "/path/to/dtsa-mcp-server/.venv/bin/python",
  "args": ["/path/to/dtsa-mcp-server/mcp_server.py"],
  "env": {
    "PYTHONPATH": "/path/to/dtsa-mcp-server"
  }
}
```

### Step 7 — Verify

Same as macOS Step 7.

---

## Getting the repositories

The code investigation tools (`dtsa_read_file`, `dtsa_grep_repo`, `dtsa_github_commits`, `dtsa_github_diff`) need local clones of all 5 ZoomRx repositories.

**Where the repos live:**

| Repository | Host |
|---|---|
| `digitrace-chrome-extension` | Phabricator (`phab.zoomrx.com`) |
| `perxcept-ios` | Phabricator (`phab.zoomrx.com`) |
| `perxcept-macos` | Phabricator (`phab.zoomrx.com`) |
| `perxcept-data-processing-service` | Phabricator (`phab.zoomrx.com`) |
| `perxcept-ap-server` | GitHub (`github.com/ZoomRx`) |

**Prerequisites:**
- `git` installed
- A Phabricator account on `phab.zoomrx.com` with access to all 4 repos — ask your team lead if you don't have one
- A GitHub account with access to the ZoomRx org (for `perxcept-ap-server`)

### macOS / Linux

```bash
bash /path/to/dtsa-mcp-server/clone_repos.sh ~/zoomrx-repos
```

This clones all 5 repos into `~/zoomrx-repos` (or pass a different path as the argument).
It is safe to re-run — existing repos will be updated with `git pull` instead of re-cloned.

Then add this to your `.env`:
```
DTSA_LOCAL_REPOS_BASE=/Users/yourname/zoomrx-repos
```

### Windows

```
C:\path\to\dtsa-mcp-server\clone_repos.bat C:\Tools\zoomrx-repos
```

Then add this to your `.env`:
```
DTSA_LOCAL_REPOS_BASE=C:\Tools\zoomrx-repos
```

### Manual clone (any OS)

If you prefer to clone manually:
```bash
mkdir ~/zoomrx-repos
git clone http://phab.zoomrx.com/source/digitrace-chrome-extension.git       ~/zoomrx-repos/digitrace-chrome-extension
git clone http://phab.zoomrx.com/source/perxcept-ios.git                     ~/zoomrx-repos/perxcept-ios
git clone http://phab.zoomrx.com/source/perxcept-macos.git                   ~/zoomrx-repos/perxcept-macos
git clone http://phab.zoomrx.com/source/perxcept-data-processing-service.git ~/zoomrx-repos/perxcept-data-processing-service
git clone https://github.com/ZoomRx/perxcept-ap-server.git                   ~/zoomrx-repos/perxcept-ap-server
```

### Phabricator clone fails?

If you get a `403` or authentication error on the Phabricator repos:
1. Log in to `phab.zoomrx.com`
2. Go to **Settings → VCS Password** and set a password for HTTP git access
3. Re-run the clone — git will prompt for your Phabricator username and VCS password

Or ask your team lead to verify you have **Observer** or higher access to each repository in Phabricator.

---

## Credentials reference

| Variable | What it is | Required |
|---|---|---|
| `DTSA_EXTENSION_DB_READ_HOST` | Extension DB hostname | Yes |
| `DTSA_EXTENSION_DB_READ_USERNAME` | DB username | Yes |
| `DTSA_EXTENSION_DB_READ_PASSWORD` | DB password | Yes |
| `DTSA_PHABRICATOR_API_TOKEN` | Phabricator Conduit token | Yes |
| `DTSA_PHABRICATOR_API_URL` | Phabricator base URL | Yes |
| `DTSA_GITHUB_TOKEN` | GitHub PAT with `repo:read` scope | Optional — only covers `perxcept-ap-server` |
| `DTSA_LOCAL_REPOS_BASE` | Path to local clones of all 5 repos | **Recommended** |

**Strongly recommend `DTSA_LOCAL_REPOS_BASE`** — 4 of 5 repos are on Phabricator (not GitHub), so a GitHub token only covers 1 of 5 repositories. Use `clone_repos.sh` / `clone_repos.bat` to get all repos locally.

---

## Troubleshooting

**No tools listed in Claude Desktop**
- Check `.env` exists and is filled in correctly
- Check `claude_desktop_config.json` has valid JSON (no trailing commas)
- Windows: all backslashes must be doubled (`\\`)

**"No module named 'config'"**
- The `PYTHONPATH` in the config must point to the `dtsa-mcp-server` folder itself

**"Connection error" on DB query**
- DB credentials in `.env` are wrong — re-check with your team

**Playwright crashes on Linux**
- Run: `.venv/bin/python -m playwright install-deps chromium`

**Skills not activating (`/dtsa` not recognized)**
- Verify skills are in `~/.claude/skills/` (macOS/Linux) or `%USERPROFILE%\.claude\skills\` (Windows)
- Each skill folder must contain a `SKILL.md` file

**Test the server manually:**
```bash
# macOS / Linux
/path/to/dtsa-mcp-server/.venv/bin/python /path/to/dtsa-mcp-server/mcp_server.py

# Windows
C:\path\to\dtsa-mcp-server\.venv\Scripts\python.exe C:\path\to\dtsa-mcp-server\mcp_server.py
```
Any error prints here. Share the output with your team.

---

## Keeping it updated

When you receive an updated zip:
1. **Copy your `.env` out first**
2. Replace the `dtsa-mcp-server` folder
3. Re-run Step 3 (dependencies may have changed)
4. Re-run Step 5 (skills may have been updated)
5. Restart Claude Desktop

Your `.env` is yours — never share it.
