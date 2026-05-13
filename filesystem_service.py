"""DTSA filesystem service — read files and search repos.

Scoped strictly to DTSA_LOCAL_REPOS_BASE. No writes, no deletes,
no access outside the configured repos base.
"""
import logging
import re
from pathlib import Path

from config import env

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    # Source code
    ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
    ".py", ".rb", ".go", ".java", ".swift", ".kt",
    # Config / markup
    ".json", ".yaml", ".yml", ".toml", ".ini", ".env.example",
    # Docs
    ".md", ".txt", ".rst",
    # Web
    ".html", ".css",
}

MAX_FILE_BYTES = 200 * 1024   # 200 KB per file read
MAX_GREP_RESULTS = 200        # max matching lines per grep
MAX_GLOB_RESULTS = 500        # max file paths per list


class DtsaFilesystemService:

    @staticmethod
    def _repos_base() -> Path:
        return Path(env.DTSA_LOCAL_REPOS_BASE).resolve()

    @staticmethod
    def _resolve_safe(path: str) -> Path | None:
        """Resolve path and confirm it sits under DTSA_LOCAL_REPOS_BASE."""
        base = DtsaFilesystemService._repos_base()
        try:
            resolved = (base / path).resolve()
        except Exception:
            return None
        try:
            resolved.relative_to(base)
            return resolved
        except ValueError:
            return None  # path escapes sandbox

    @staticmethod
    async def read_file(path: str, start_line: int = 1, end_line: int | None = None) -> dict:
        resolved = DtsaFilesystemService._resolve_safe(path)
        if resolved is None:
            return {"error": f"Path '{path}' is outside the allowed repos base or invalid"}
        if not resolved.exists():
            return {"error": f"File not found: {path}"}
        if not resolved.is_file():
            return {"error": f"Not a file: {path}"}
        if resolved.suffix.lower() not in ALLOWED_EXTENSIONS:
            return {"error": f"File type '{resolved.suffix}' is not readable by DTSA"}

        size = resolved.stat().st_size
        if size > MAX_FILE_BYTES:
            return {
                "error": (
                    f"File is {size // 1024}KB — above the {MAX_FILE_BYTES // 1024}KB limit. "
                    "Use start_line/end_line to read a specific section."
                ),
                "total_lines_hint": "Run grep_in_repo first to find the relevant section.",
            }

        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"error": f"Could not read file: {e}"}

        lines = content.splitlines(keepends=True)
        total_lines = len(lines)
        start = max(1, start_line) - 1
        end = min(total_lines, end_line) if end_line else total_lines
        selected = lines[start:end]
        numbered = "".join(f"{start + i + 1:4d} | {line}" for i, line in enumerate(selected))

        return {
            "path": path,
            "total_lines": total_lines,
            "showing_lines": f"{start + 1}–{end}",
            "content": numbered,
            "truncated": end < total_lines,
        }

    @staticmethod
    async def grep_in_repo(
        repo_name: str,
        pattern: str,
        file_glob: str = "**/*",
        case_sensitive: bool = False,
        context_lines: int = 2,
    ) -> dict:
        base = DtsaFilesystemService._repos_base()
        repo_path = (base / repo_name).resolve()

        try:
            repo_path.relative_to(base)
        except ValueError:
            return {"error": f"Repo '{repo_name}' is outside the allowed repos base"}

        if not repo_path.is_dir():
            return {"error": f"Repository directory not found: {repo_name}"}

        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            compiled = re.compile(pattern, flags)
        except re.error as e:
            return {"error": f"Invalid regex pattern: {e}"}

        matches: list[dict] = []
        files_searched = 0
        skipped_files: list[str] = []

        for filepath in sorted(repo_path.glob(file_glob)):
            if len(matches) >= MAX_GREP_RESULTS:
                break
            if not filepath.is_file():
                continue
            if filepath.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            parts = filepath.relative_to(repo_path).parts
            if any(p.startswith(".") or p in ("node_modules", "__pycache__", "dist", "build") for p in parts):
                continue

            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                skipped_files.append(str(filepath.relative_to(base)))
                continue

            files_searched += 1
            file_lines = content.splitlines()

            for line_num, line in enumerate(file_lines):
                if compiled.search(line):
                    ctx_start = max(0, line_num - context_lines)
                    ctx_end = min(len(file_lines), line_num + context_lines + 1)
                    context_block = []
                    for i in range(ctx_start, ctx_end):
                        prefix = ">>>" if i == line_num else "   "
                        context_block.append(f"{prefix} {i + 1:4d} | {file_lines[i]}")

                    matches.append({
                        "file": str(filepath.relative_to(base)),
                        "line": line_num + 1,
                        "match": line.strip()[:300],
                        "context": "\n".join(context_block),
                    })

                    if len(matches) >= MAX_GREP_RESULTS:
                        break

        return {
            "repo": repo_name,
            "pattern": pattern,
            "files_searched": files_searched,
            "match_count": len(matches),
            "matches": matches,
            "truncated": len(matches) >= MAX_GREP_RESULTS,
            "skipped_unreadable": len(skipped_files),
        }

    @staticmethod
    async def list_repo_files(
        repo_name: str,
        subpath: str = "",
        file_glob: str = "**/*",
    ) -> dict:
        base = DtsaFilesystemService._repos_base()
        target = (base / repo_name / subpath).resolve() if subpath else (base / repo_name).resolve()

        try:
            target.relative_to(base)
        except ValueError:
            return {"error": "Path escapes the allowed repos base"}

        if not target.exists():
            return {"error": f"Path not found: {repo_name}/{subpath}"}

        results: list[str] = []
        for p in sorted(target.glob(file_glob)):
            if not p.is_file():
                continue
            parts = p.relative_to(target).parts
            if any(part.startswith(".") or part in ("node_modules", "__pycache__", "dist", "build") for part in parts):
                continue
            if p.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            results.append(str(p.relative_to(base)))
            if len(results) >= MAX_GLOB_RESULTS:
                break

        return {
            "repo": repo_name,
            "subpath": subpath or "(root)",
            "glob": file_glob,
            "file_count": len(results),
            "files": results,
            "truncated": len(results) >= MAX_GLOB_RESULTS,
        }
