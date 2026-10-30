"""Explicit optional DTSA actions. SQL uses the native Perxcept MCP instead."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

SERVER = Path(__file__).resolve().parent / "server"
sys.path.insert(0, str(SERVER))
REPOS = {"digitrace-chrome-extension", "perxcept-ap-server", "perxcept-ios", "perxcept-macos", "perxcept-data-processing-service"}
ACTIONS = {
    "dtsa_playwright_selector": ("playwright_service", "DtsaPlaywrightService", "test_selector", {"url", "selector"}, {"selector_type"}),
    "dtsa_github_commits": ("github_service", "DtsaGithubService", "get_commits", {"repo_name", "since", "until"}, {"path_filter"}),
    "dtsa_github_diff": ("github_service", "DtsaGithubService", "get_diff", {"repo_name", "commit_hash"}, set()),
    "dtsa_read_file": ("filesystem_service", "DtsaFilesystemService", "read_file", {"path"}, {"start_line", "end_line"}),
    "dtsa_grep_repo": ("filesystem_service", "DtsaFilesystemService", "grep_in_repo", {"repo_name", "pattern"}, {"file_glob", "case_sensitive", "context_lines"}),
    "dtsa_list_repo_files": ("filesystem_service", "DtsaFilesystemService", "list_repo_files", {"repo_name"}, {"subpath", "file_glob"}),
    "dtsa_phabricator_create_task": ("phabricator_service", "DtsaPhabricatorService", "create_task", {"title", "description", "priority"}, {"tags"}),
}


def validate(action, data, allow_ticket_write=False):
    if not isinstance(data, dict):
        raise ValueError("Action input must be a JSON object")
    _, _, _, required, optional = ACTIONS[action]
    if not required.issubset(data) or set(data) - required - optional:
        raise ValueError("Missing or unexpected action arguments; credentials are not accepted in action JSON")
    for key in required:
        if not isinstance(data[key], str) or not data[key]:
            raise ValueError(f"{key} must be a nonempty string")
    if "repo_name" in data and data["repo_name"] not in REPOS:
        raise ValueError("Repository is outside the declared five tracker repositories")
    for key in ("start_line", "end_line", "context_lines"):
        if key in data and (type(data[key]) is not int or data[key] < (0 if key == "context_lines" else 1)):
            raise ValueError(f"Invalid {key}")
    if "context_lines" in data and data["context_lines"] > 20:
        raise ValueError("context_lines must not exceed 20")
    if "start_line" in data and "end_line" in data and data["end_line"] < data["start_line"]:
        raise ValueError("end_line precedes start_line")
    if "case_sensitive" in data and type(data["case_sensitive"]) is not bool:
        raise ValueError("case_sensitive must be a boolean")
    for key in ("tags", "path_filter"):
        if key in data and (not isinstance(data[key], list) or any(not isinstance(v, str) for v in data[key])):
            raise ValueError(f"{key} must be a list of strings")
    if action == "dtsa_playwright_selector":
        url = urlsplit(data["url"])
        if url.scheme not in ("https", "http") or not url.hostname or url.username or url.password:
            raise ValueError("Selector URL must be an explicit HTTP(S) page without embedded credentials")
        if data.get("selector_type", "css") not in ("css", "xpath"):
            raise ValueError("selector_type must be css or xpath")
    if action == "dtsa_phabricator_create_task":
        if not allow_ticket_write:
            raise PermissionError("Ticket creation requires explicit user authorization and --allow-ticket-write")
        if data["priority"] not in ("unbreak_now", "high", "normal", "low"):
            raise ValueError("Invalid ticket priority")
        url = urlsplit(os.environ.get("DTSA_PHABRICATOR_API_URL", ""))
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("Configure an approved HTTPS Phabricator base URL")
    needs_repos = action in {"dtsa_read_file", "dtsa_grep_repo", "dtsa_list_repo_files"} or (
        action in {"dtsa_github_commits", "dtsa_github_diff"} and not os.environ.get("DTSA_GITHUB_TOKEN"))
    if needs_repos:
        configured = os.environ.get("DTSA_LOCAL_REPOS_BASE", "")
        if not configured:
            raise ValueError("DTSA_LOCAL_REPOS_BASE is not configured")
        try:
            base = Path(configured).resolve(strict=True)
        except OSError as exc:
            # Restricted hosts can deny DOS volume-name conversion while
            # allowing ordinary handles. Only repo reads have a same-handle
            # implementation; external Git continues requiring its existing
            # strict canonical DOS contract.
            if os.name != "nt" or getattr(exc, "winerror", None) != 5:
                raise
            if action not in {"dtsa_read_file", "dtsa_grep_repo", "dtsa_list_repo_files"}:
                raise ValueError("Local Git requires strict Windows DOS canonicalization; this host denied it. Use authorized GitHub API access or an ordinary terminal.") from None
            from windows_repo_scope import WindowsRepoScope
            with WindowsRepoScope(configured) as scope:
                if action == "dtsa_read_file":
                    with scope.target(data["path"]):
                        pass
                else:
                    scope.validate_directory(data["repo_name"]+("/"+data["subpath"] if data.get("subpath") else ""))
            return
        if not base.is_dir() or base == Path(base.anchor) or base == Path.home().resolve():
            raise ValueError("Configure a dedicated authorized repository base")
        if action == "dtsa_read_file":
            relative = Path(data["path"])
            if relative.is_absolute() or not relative.parts or relative.parts[0] not in REPOS:
                raise ValueError("File must be relative to one of the five tracker repositories")
            target = (base / relative).resolve()
        else:
            target = (base / data["repo_name"] / data.get("subpath", "")).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            raise ValueError("Repository path escapes the configured base") from None


def sanitized(value):
    text = json.dumps(value, default=str, ensure_ascii=False)
    for key in ("DTSA_GITHUB_TOKEN", "DTSA_PHABRICATOR_API_TOKEN"):
        secret = os.environ.get(key, "")
        if secret:
            text = text.replace(secret, "[redacted]")
    return text


async def dispatch(action, data, allow_ticket_write=False):
    validate(action, data, allow_ticket_write)
    import importlib
    module, service, method, _, _ = ACTIONS[action]
    selected = importlib.import_module(module)
    return await getattr(getattr(selected, service), method)(**data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", required=True, choices=sorted(ACTIONS))
    parser.add_argument("--input", required=True, help="JSON file containing only action arguments")
    parser.add_argument("--allow-ticket-write", action="store_true", help="Use only after explicit authorization for this ticket")
    args = parser.parse_args()
    write_attempted = False
    try:
        input_path = Path(args.input)
        if input_path.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("Action input exceeds 2 MiB")
        data = json.loads(input_path.read_text(encoding="utf-8-sig"))
        validate(args.action, data, args.allow_ticket_write)
        write_attempted = args.action == "dtsa_phabricator_create_task"
        result = asyncio.run(dispatch(args.action, data, args.allow_ticket_write))
        failed = isinstance(result, dict) and ("error" in result or result.get("success") is False)
        print(sanitized({"action": args.action, "status": "failed" if failed else "ok", "writeAttempted": write_attempted, "result": result}))
        return 1 if failed else 0
    except ImportError as exc:
        print(sanitized({"action": args.action, "status": "optional_dependency_missing", "module": exc.name, "writeAttempted": write_attempted}))
        return 2
    except Exception as exc:
        print(sanitized({"action": args.action, "status": "failed", "error": str(exc), "writeAttempted": write_attempted}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
