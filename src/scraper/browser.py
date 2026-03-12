from __future__ import annotations

import logging
import random

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from config.settings import BROWSER_DATA_DIR

logger = logging.getLogger(__name__)

# Stealth settings
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Common cookie consent button selectors (GDPR banners)
_COOKIE_ACCEPT_SELECTORS = [
    "button#onetrust-accept-btn-handler",
    "button[data-testid='accept-cookies']",
    "button.cookie-accept",
    "button[class*='accept']",
    "a[class*='accept']",
    "#ccc-notify-accept",
    "#ccc-recommended-settings",
    ".ccc-accept-button",
    "button[aria-label*='accept']",
    "button[aria-label*='Accept']",
    "button:has-text('Accept')",
    "button:has-text('Accept All')",
    "button:has-text('Accept all')",
    "button:has-text('Got it')",
    "button:has-text('I agree')",
    "button:has-text('OK')",
]


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

            # Dismiss cookie consent banners
            await self._dismiss_cookie_banner(page)

            # Wait for actual booking content to render (SPA may still be loading)
            await self._wait_for_content(page)

            # Random delay to appear human
            await page.wait_for_timeout(random.randint(1000, 3000))
        except Exception:
            await page.close()
            raise

        return page

    async def _dismiss_cookie_banner(self, page: Page) -> None:
        """Try to dismiss cookie consent banners."""
        for selector in _COOKIE_ACCEPT_SELECTORS:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=500):
                    await btn.click(timeout=2000)
                    logger.info("Dismissed cookie banner via: %s", selector)
                    await page.wait_for_timeout(500)
                    return
            except Exception:
                continue

    async def _wait_for_content(self, page: Page, timeout_ms: int = 10_000) -> None:
        """Wait for booking content to appear in the DOM.

        Polls for time patterns (HH:MM) in the page body text, which indicates
        that the SPA has finished rendering booking slots.
        """
        try:
            await page.wait_for_function(
                """
                () => {
                    const body = document.body ? document.body.innerText : '';
                    const timePattern = /\\d{1,2}:\\d{2}/;
                    return timePattern.test(body);
                }
                """,
                timeout=timeout_ms,
            )
            logger.debug("Content with time patterns detected")
        except Exception:
            logger.warning(
                "Timed out waiting for time patterns in page content "
                "(page may be empty or structure changed)"
            )
