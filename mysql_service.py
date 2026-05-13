"""DTSA MySQL read-only query service."""
import logging
import re

from sqlalchemy import text

from dtsa_database import get_extension_read_db

logger = logging.getLogger(__name__)

FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|REPLACE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


class DtsaMysqlService:
    @staticmethod
    async def execute_read_query(query: str, params: dict, max_rows: int = 100) -> dict:
        if FORBIDDEN.search(query):
            return {"error": "Only SELECT queries are allowed", "query": query}
        if not query.strip().upper().startswith("SELECT"):
            return {"error": "Query must start with SELECT", "query": query}

        max_rows = min(max_rows, 100)

        try:
            with get_extension_read_db() as session:
                session.execute(text("SET SESSION MAX_EXECUTION_TIME=30000"))
                if "LIMIT" not in query.upper():
                    query = f"{query.rstrip(';')} LIMIT {max_rows}"
                result = session.execute(text(query), params)
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                return {
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "query_executed": query,
                    "truncated": len(rows) >= max_rows,
                }
        except Exception as e:
            logger.error(f"[DTSA] MySQL query failed: {e}")
            return {"error": str(e), "query": query}
