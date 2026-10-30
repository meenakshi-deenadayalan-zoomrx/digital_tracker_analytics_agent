# Perxcept connection and optional diagnostics setup

## SQL connection

Use the client's configured native `prod-perxcept-mysql-mcp` connection. Initial Entra authorization may be necessary for this new server. A missing tool or access denial requires the central MCP registration or Entra assignment to be corrected. Do not install a local DB worker, reset other sessions, import Vault credentials, restore a uv launcher, or edit global Python/PATH. Read `references/remote-sql.md` before queries.

## Optional diagnostic actions

SQL volume checks need no local Python. Selector, repository and ticket branches use the retained optional services through `scripts/diagnostic-actions.py`; they are not automatically installed or run by this skill and never block SQL checks. On Galen Windows use `galen-python <absolute-skill-path>\scripts\diagnostic-actions.py --help`. Outside Galen use an explicitly configured supported Python interpreter; do not replace a working generic `python` alias.

Write a JSON input file containing only the action arguments and pass `--action ACTION --input <file.json>`. The adapter accepts the historical action names: `dtsa_playwright_selector`, `dtsa_github_commits`, `dtsa_github_diff`, `dtsa_read_file`, `dtsa_grep_repo`, `dtsa_list_repo_files`, `dtsa_phabricator_create_task`. SQL is deliberately absent. It emits JSON and reports missing optional dependencies clearly; it does not install anything.

- Repository file reads: standard-library Python and `DTSA_LOCAL_REPOS_BASE` pointing to authorized clones. The filesystem scope must be a real explicit repository base, not the home folder. Read the relevant AGENT_CONTEXT first. Clone only on explicit authorization using `scripts/clone_repos.bat` or `scripts/clone_repos.sh`, an approved `DTSA_PHAB_BASE` and existing Git access. Existing clones may be fast-forward updated; don't invoke the clone scripts merely to read files.
- Commit/diff operations: Git + GitPython for local clones, or httpx and an optional existing `DTSA_GITHUB_TOKEN` for the declared GitHub repository API. GitHub does not cover the four Phabricator clones. Keep credentials in the process environment; never place them in action JSON.
- Selector operations: Playwright and Chromium already installed in the selected interpreter. A tracker selector browser is optional workflow testing, not a DB or AP authentication browser. This release performs no browser download, session import or browser startup except the explicit selector operation. See `scripts/optional.requirements.txt` for the dependency list; IT may provision those separately. Bot detection is INCONCLUSIVE, never bypassed.
- Tickets: httpx plus approved HTTPS `DTSA_PHABRICATOR_API_URL` and `DTSA_PHABRICATOR_API_TOKEN` in the process environment. Draft a local report first. Invoke only after explicit user authorization for that concrete ticket, with `--allow-ticket-write`. No automatic retry: after an uncertain response check the remote ticket list before another create.

The central Perxcept tool provides SQL only. Optional integrations retain their previous algorithms but still require their own successful checks. A shell/sandbox failure prevents optional local operations and is not a DB sign-in error.
