"""DTSA Playwright selector validation service."""
import asyncio
import logging
import random

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

BOT_SIGS = [
    "cf-browser-verification",
    "challenge-platform",
    "g-recaptcha",
    "hcaptcha",
    "cloudflare",
    "access denied",
    "please verify you are a human",
]


class DtsaPlaywrightService:
    @staticmethod
    async def test_selector(url: str, selector: str, selector_type: str = "css") -> dict:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                ctx = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = await ctx.new_page()

                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                except Exception as e:
                    await browser.close()
                    return {"url": url, "selector": selector, "error": f"Navigation failed: {e}", "found": False}

                await asyncio.sleep(random.uniform(0.5, 1.5))
                content = await page.content()
                blocked = any(s in content.lower() for s in BOT_SIGS)

                if blocked:
                    await browser.close()
                    return {
                        "url": url,
                        "selector": selector,
                        "found": False,
                        "blocked": True,
                        "element_count": 0,
                        "note": "Bot detection triggered — INCONCLUSIVE",
                    }

                loc = f"xpath={selector}" if selector_type == "xpath" else selector
                elements = await page.locator(loc).all()
                count = len(elements)
                await browser.close()

                return {
                    "url": url,
                    "selector": selector,
                    "selector_type": selector_type,
                    "found": count > 0,
                    "element_count": count,
                    "blocked": False,
                }
        except Exception as e:
            logger.error(f"[DTSA] Playwright selector test failed: {e}")
            return {"url": url, "selector": selector, "error": str(e), "found": False}
