"""Core monitoring logic: check links, find matching slots, send alerts."""

from __future__ import annotations

import logging

from telegram.ext import ContextTypes

from src.bot.formatters import format_slot_alert
from src.monitor.state import StateManager
from src.scraper.availability import AvailabilityFetcher

logger = logging.getLogger(__name__)


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

        unique_urls = list({l.url for l in active_links})
        all_slots = await self._fetcher.fetch_multiple(unique_urls)

        for link in active_links:
            slots = all_slots.get(link.url, [])
            if not slots:
                continue

            matching = [s for s in slots if link.matches_slot(s)]

            if matching:
                logger.info(
                    "Found %d matching slots for link %s (%s)",
                    len(matching), link.id, link.time_description,
                )
                msg = format_slot_alert(link, matching)
                try:
                    await context.bot.send_message(
                        chat_id=self._chat_id,
                        text=msg,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                except Exception:
                    logger.exception("Failed to send alert for link %s", link.id)
        logger.info("Check cycle complete")
