from __future__ import annotations

import asyncio
import logging
import random

from src.models.types import TimeSlot
from src.scraper.browser import BrowserManager
from src.scraper.parser import parse_availability

logger = logging.getLogger(__name__)


class AvailabilityFetcher:
    def __init__(self, browser: BrowserManager) -> None:
        self._browser = browser

    async def fetch_url(self, url: str) -> list[TimeSlot]:
        """Fetch availability for a direct URL. Returns list of parsed slots."""
        page = None
        try:
            page = await self._browser.load_page(url)
            slots = await parse_availability(page)

            # If no slots found, wait a bit more and retry parsing once.
            # Some SPAs render content with a delay after networkidle.
            if not slots:
                logger.info("No slots on first parse, waiting 5s and retrying...")
                await page.wait_for_timeout(5000)
                slots = await parse_availability(page)

            return slots
        except Exception:
            logger.exception("Failed to fetch %s", url)
            return []
        finally:
            if page:
                await page.close()

    async def fetch_url_with_retry(self, url: str, max_retries: int = 2) -> list[TimeSlot]:
        """Fetch with retries and exponential backoff."""
        for attempt in range(max_retries + 1):
            slots = await self.fetch_url(url)
            if slots:
                return slots
            if attempt < max_retries:
                wait = (attempt + 1) * 5
                logger.warning("Retry %d for %s in %ds", attempt + 1, url, wait)
                await asyncio.sleep(wait)

        logger.error("All retries failed for %s", url)
        return []

    async def fetch_multiple(self, urls: list[str], max_retries: int = 2) -> dict[str, list[TimeSlot]]:
        """Fetch availability for multiple URLs sequentially.

        Returns a dict keyed by URL.
        """
        results: dict[str, list[TimeSlot]] = {}

        for url in urls:
            slots = await self.fetch_url_with_retry(url, max_retries)
            results[url] = slots

            # Delay between requests to avoid detection
            await asyncio.sleep(random.uniform(3, 8))

        return results
