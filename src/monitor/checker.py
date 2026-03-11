"""Core monitoring logic: check links, find matching slots, send alerts."""

from __future__ import annotations

import logging

from telegram.ext import ContextTypes

from src.bot.formatters import format_slot_alert
from src.models.types import MonitoredLink, TimeSlot
from src.monitor.state import StateManager
from src.scraper.availability import AvailabilityFetcher

logger = logging.getLogger(__name__)


def _slot_matches_time(slot: TimeSlot, link: MonitoredLink) -> bool:
    """Check if a slot matches the desired time for a link."""
    if not slot.is_available:
        return False
    return slot.start_time == link.desired_time


class AvailabilityChecker:
    def __init__(
        self,
        fetcher: AvailabilityFetcher,
        state: StateManager,
        chat_id: int,
    ) -> None:
        self._fetcher = fetcher
        self._state = state
        self._chat_id = chat_id

    async def check_all_links(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        state = self._state.load()
        if not state.monitoring_enabled:
            logger.debug("Monitoring is paused, skipping check")
            return

        active_links = [l for l in state.links if l.active]
        if not active_links:
            logger.debug("No active links to monitor")
            return

        logger.info("Checking %d active links", len(active_links))

        # Collect unique URLs (multiple links might point to the same page)
        unique_urls = list({l.url for l in active_links})

        # Fetch all pages
        all_slots = await self._fetcher.fetch_multiple(unique_urls)

        # Check each link
        for link in active_links:
            slots = all_slots.get(link.url, [])
            if not slots:
                continue

            matching = [s for s in slots if _slot_matches_time(s, link)]

            # Check against already notified
            notified_keys = set(state.notified.get(link.id, []))
            new_slots = [s for s in matching if s.key not in notified_keys]

            if new_slots:
                logger.info(
                    "Found %d new matching slots for link %s (%s)",
                    len(new_slots), link.id, link.desired_time.strftime("%H:%M"),
                )
                msg = format_slot_alert(link, new_slots)
                try:
                    await context.bot.send_message(
                        chat_id=self._chat_id,
                        text=msg,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                except Exception:
                    logger.exception("Failed to send alert for link %s", link.id)

            # Update notified with ALL currently matching slots
            state.notified[link.id] = [s.key for s in matching]

        self._state.save(state)
        logger.info("Check cycle complete")
