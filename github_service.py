"""DTSA GitHub commit analysis service.

Uses local git repositories via gitpython by default.
Set DTSA_GITHUB_TOKEN in .env to switch to the GitHub API instead.
"""
import logging
import os
from datetime import datetime, timezone

from config import env

logger = logging.getLogger(__name__)

ALLOWED_REPOS = {
    "digitrace-chrome-extension",
    "perxcept-ap-server",
    "perxcept-ios",
    "perxcept-macos",
    "perxcept-data-processing-service",
}

GITHUB_API = "https://api.github.com"


def _use_github_api() -> bool:
    return bool(env.DTSA_GITHUB_TOKEN)


def _local_repo_path(repo_name: str) -> str:
    return os.path.join(env.DTSA_LOCAL_REPOS_BASE, repo_name)


class DtsaGithubService:

    @staticmethod
    async def get_commits(
        repo_name: str,
        since: str,
        until: str,
        path_filter: list[str] | None = None,
    ) -> dict:
        if repo_name not in ALLOWED_REPOS:
            return {"error": f"Repository '{repo_name}' not in allowed list"}
        if _use_github_api():
            return await DtsaGithubService._github_get_commits(repo_name, since, until, path_filter)
        return DtsaGithubService._local_get_commits(repo_name, since, until, path_filter)

    @staticmethod
    async def get_diff(repo_name: str, commit_hash: str) -> dict:
        if repo_name not in ALLOWED_REPOS:
            return {"error": f"Repository '{repo_name}' not in allowed list"}
        if _use_github_api():
            return await DtsaGithubService._github_get_diff(repo_name, commit_hash)
        return DtsaGithubService._local_get_diff(repo_name, commit_hash)

    # ------------------------------------------------------------------ #
    # Local git (gitpython)                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_iso(dt_str: str) -> datetime:
        dt_str = dt_str.rstrip("Z")
        if "+" in dt_str:
            dt_str = dt_str.split("+")[0]
        return datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)

    @staticmethod
    def _local_get_commits(
        repo_name: str,
        since: str,
        until: str,
        path_filter: list[str] | None,
    ) -> dict:
        try:
            import git

            repo_path = _local_repo_path(repo_name)
            if not os.path.isdir(repo_path):
                return {"error": f"Local repo not found at {repo_path}", "repo_name": repo_name}

            repo = git.Repo(repo_path)
            since_dt = DtsaGithubService._parse_iso(since)
            until_dt = DtsaGithubService._parse_iso(until)

            kwargs: dict = {
                "after": since_dt.isoformat(),
                "before": until_dt.isoformat(),
                "max_count": 100,
            }
            if path_filter:
                kwargs["paths"] = path_filter

            commits = []
            for c in repo.iter_commits("HEAD", **kwargs):
                commits.append({
                    "hash": c.hexsha[:8],
                    "full_hash": c.hexsha,
                    "author": c.author.name,
                    "timestamp": datetime.fromtimestamp(c.committed_date, tz=timezone.utc).isoformat(),
                    "message": c.message[:500],
                })

            commits.sort(key=lambda x: x["timestamp"], reverse=True)
            return {
                "repo_name": repo_name,
                "since": since,
                "until": until,
                "commits": commits,
                "total_count": len(commits),
                "source": "local_git",
            }
        except Exception as e:
            logger.error(f"[DTSA] Local git commits failed for {repo_name}: {e}")
            return {"error": str(e), "repo_name": repo_name}

    @staticmethod
    def _local_get_diff(repo_name: str, commit_hash: str) -> dict:
        try:
            import git

            repo_path = _local_repo_path(repo_name)
            if not os.path.isdir(repo_path):
                return {"error": f"Local repo not found at {repo_path}", "repo_name": repo_name}

            repo = git.Repo(repo_path)
            commit = repo.commit(commit_hash)
            parent = commit.parents[0] if commit.parents else repo.tree("4b825dc")

            diffs = parent.diff(commit, create_patch=True)
            files = []
            for diff in diffs:
                patch = ""
                try:
                    patch = diff.diff.decode("utf-8", errors="replace")
                except Exception:
                    patch = "[binary or undecodable diff]"
                if len(patch) > 5000:
                    patch = patch[:5000] + "\n... [truncated]"
                files.append({
                    "filename": diff.b_path or diff.a_path,
                    "status": diff.change_type,
                    "additions": patch.count("\n+"),
                    "deletions": patch.count("\n-"),
                    "patch": patch,
                })

            return {
                "commit_hash": commit_hash,
                "repo_name": repo_name,
                "message": commit.message[:500],
                "author": commit.author.name,
                "timestamp": datetime.fromtimestamp(commit.committed_date, tz=timezone.utc).isoformat(),
                "files": files,
                "total_files_changed": len(files),
                "source": "local_git",
            }
        except Exception as e:
            logger.error(f"[DTSA] Local git diff failed for {repo_name}@{commit_hash}: {e}")
            return {"error": str(e), "repo_name": repo_name, "commit_hash": commit_hash}

    # ------------------------------------------------------------------ #
    # GitHub API (used when DTSA_GITHUB_TOKEN is set)                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _headers() -> dict:
        return {
            "Authorization": f"Bearer {env.DTSA_GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    @staticmethod
    async def _github_get_commits(
        repo_name: str,
        since: str,
        until: str,
        path_filter: list[str] | None,
    ) -> dict:
        try:
            import httpx

            url = f"{GITHUB_API}/repos/{env.DTSA_GITHUB_ORG}/{repo_name}/commits"
            params: dict = {"since": since, "until": until, "per_page": 100}
            if path_filter:
                params["path"] = path_filter[0]

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, headers=DtsaGithubService._headers(), params=params)
                resp.raise_for_status()

            commits = [
                {
                    "hash": c["sha"][:8],
                    "full_hash": c["sha"],
                    "author": c["commit"]["author"]["name"],
                    "timestamp": c["commit"]["author"]["date"],
                    "message": c["commit"]["message"][:500],
                }
                for c in resp.json()[:100]
            ]
            commits.sort(key=lambda x: x["timestamp"], reverse=True)
            return {
                "repo_name": repo_name,
                "since": since,
                "until": until,
                "commits": commits,
                "total_count": len(commits),
                "source": "github_api",
            }
        except Exception as e:
            logger.error(f"[DTSA] GitHub API commits failed: {e}")
            return {"error": str(e), "repo_name": repo_name}

    @staticmethod
    async def _github_get_diff(repo_name: str, commit_hash: str) -> dict:
        try:
            import httpx

            url = f"{GITHUB_API}/repos/{env.DTSA_GITHUB_ORG}/{repo_name}/commits/{commit_hash}"
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, headers=DtsaGithubService._headers())
                resp.raise_for_status()

            data = resp.json()
            files = []
            for f in data.get("files", []):
                patch = f.get("patch", "")
                if len(patch) > 5000:
                    patch = patch[:5000] + "\n... [truncated]"
                files.append({
                    "filename": f["filename"],
                    "status": f["status"],
                    "additions": f["additions"],
                    "deletions": f["deletions"],
                    "patch": patch,
                })

            return {
                "commit_hash": commit_hash,
                "repo_name": repo_name,
                "message": data["commit"]["message"][:500],
                "author": data["commit"]["author"]["name"],
                "timestamp": data["commit"]["author"]["date"],
                "files": files,
                "total_files_changed": len(files),
                "source": "github_api",
            }
        except Exception as e:
            logger.error(f"[DTSA] GitHub API diff failed: {e}")
            return {"error": str(e), "repo_name": repo_name, "commit_hash": commit_hash}
