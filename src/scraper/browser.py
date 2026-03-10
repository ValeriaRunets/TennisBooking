from __future__ import annotations

import logging
import random

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from config.settings import BROWSER_DATA_DIR

logger = logging.getLogger(__name__)

# Stealth settings
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


class BrowserManager:
    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def start(self, headless: bool = True) -> None:
        BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        self._context = await self._browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1366, "height": 768},
            locale="en-GB",
            timezone_id="Europe/London",
        )
        # Mask webdriver flag
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        logger.info("Browser started (headless=%s)", headless)

    async def stop(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser stopped")

    async def load_page(self, url: str, wait_selector: str | None = None) -> Page:
        if not self._context:
            raise RuntimeError("Browser not started. Call start() first.")

        page = await self._context.new_page()
        try:
            logger.debug("Loading %s", url)
            await page.goto(url, wait_until="networkidle", timeout=30_000)

            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=15_000)

            # Random delay to appear human
            await page.wait_for_timeout(random.randint(1000, 3000))
        except Exception:
            await page.close()
            raise

        return page
