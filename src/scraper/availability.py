from __future__ import annotations

import asyncio
import logging
import random
from datetime import date

from src.models.types import AvailabilitySnapshot, Location
from src.scraper.browser import BrowserManager
from src.scraper.parser import parse_availability

logger = logging.getLogger(__name__)


class AvailabilityFetcher:
    def __init__(self, browser: BrowserManager) -> None:
        self._browser = browser

    async def fetch(self, location: Location, target_date: date) -> AvailabilitySnapshot | None:
        """Fetch availability for a single location + date."""
        url = location.url_for_date(target_date)
        page = None
        try:
            page = await self._browser.load_page(url)
            slots = await parse_availability(page)
            return AvailabilitySnapshot(
                location_slug=location.slug,
                query_date=target_date,
                slots=slots,
            )
        except Exception:
            logger.exception("Failed to fetch %s", url)
            return None
        finally:
            if page:
                await page.close()

    async def fetch_batch(
        self,
        pairs: list[tuple[Location, date]],
        max_retries: int = 2,
    ) -> dict[str, AvailabilitySnapshot]:
        """Fetch availability for multiple (location, date) pairs sequentially.

        Returns a dict keyed by "location_slug:date_iso".
        """
        results: dict[str, AvailabilitySnapshot] = {}

        for location, target_date in pairs:
            key = f"{location.slug}:{target_date.isoformat()}"
            snapshot = None

            for attempt in range(max_retries + 1):
                snapshot = await self.fetch(location, target_date)
                if snapshot is not None:
                    break
                wait = (attempt + 1) * 5
                logger.warning("Retry %d for %s in %ds", attempt + 1, key, wait)
                await asyncio.sleep(wait)

            if snapshot:
                results[key] = snapshot
            else:
                logger.error("All retries failed for %s", key)

            # Delay between requests to avoid detection
            await asyncio.sleep(random.uniform(3, 8))

        return results
