"""DTSA Phabricator task creation via Conduit API."""
import logging

from config import env

logger = logging.getLogger(__name__)

PRIORITY_MAP = {
    "unbreak_now": 100,
    "high": 80,
    "normal": 50,
    "low": 25,
}


class DtsaPhabricatorService:
    @staticmethod
    async def create_task(
        title: str,
        description: str,
        priority: str,
        tags: list[str] | None = None,
    ) -> dict:
        if not env.DTSA_PHABRICATOR_API_TOKEN or not env.DTSA_PHABRICATOR_API_URL:
            return {
                "success": False,
                "error": (
                    "Phabricator credentials not configured. "
                    "Set DTSA_PHABRICATOR_API_TOKEN and DTSA_PHABRICATOR_API_URL in .env"
                ),
            }

        try:
            import httpx

            url = f"{env.DTSA_PHABRICATOR_API_URL}/api/maniphest.createtask"
            payload: dict = {
                "api.token": env.DTSA_PHABRICATOR_API_TOKEN,
                "title": title,
                "description": description,
                "priority": PRIORITY_MAP.get(priority, 50),
            }
            if tags:
                for i, tag in enumerate(tags):
                    payload[f"projectPHIDs[{i}]"] = tag

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, data=payload)
                resp.raise_for_status()

            data = resp.json()
            if data.get("error_code"):
                return {"success": False, "error": data.get("error_info")}

            task_id = data.get("result", {}).get("id")
            return {
                "success": True,
                "task_id": f"T{task_id}",
                "url": f"{env.DTSA_PHABRICATOR_API_URL}/T{task_id}",
                "priority": priority,
            }
        except Exception as e:
            logger.error(f"[DTSA] Phabricator task creation failed: {e}")
            return {"success": False, "error": str(e)}
