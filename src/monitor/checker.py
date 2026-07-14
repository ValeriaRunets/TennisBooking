"""Core monitoring logic: check links, find matching slots, send alerts."""

from __future__ import annotations

import logging

from telegram import Bot

from src.bot.formatters import format_parse_failure_warning, format_slot_alert
from src.models.types import MonitoredLink, TimeSlot
from src.monitor.state import StateManager
from src.scraper.availability import AvailabilityFetcher

logger = logging.getLogger(__name__)

# Consecutive checks yielding no slots at all before the user is warned once.
FAILURE_ALERT_THRESHOLD = 5


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

    async def check_all_links(self, bot: Bot) -> None:
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

        checked: dict[str, MonitoredLink] = {}
        for link in active_links:
            await self._process_link(bot, link, all_slots.get(link.url, []))
            checked[link.id] = link

        self._apply_updates(checked)
        logger.info("Check cycle complete")

    async def _process_link(
        self,
        bot: Bot,
        link: MonitoredLink,
        slots: list[TimeSlot],
    ) -> None:
        """Update the link's tracking fields in place and send due alerts."""
        if not slots:
            # No slots at all usually means the parser failed or the page is
            # stale (e.g. the date in the URL has passed) — a live page shows
            # booked slots too. Warn the user once after repeated failures.
            link.consecutive_failures += 1
            logger.warning(
                "No slots for link %s (%d consecutive failures)",
                link.id, link.consecutive_failures,
            )
            if (
                link.consecutive_failures >= FAILURE_ALERT_THRESHOLD
                and not link.failure_notified
            ):
                if await self._send(bot, format_parse_failure_warning(link)):
                    link.failure_notified = True
            return

        link.consecutive_failures = 0
        link.failure_notified = False

        matching = [s for s in slots if link.matches_slot(s)]
        # Forget slots that vanished (booked or gone) so they alert again
        # if they free up later.
        link.notified_keys &= {s.key for s in matching}

        new_slots = [s for s in matching if s.key not in link.notified_keys]
        if not new_slots:
            return

        logger.info(
            "Found %d new matching slots for link %s (%s)",
            len(new_slots), link.id, link.time_description,
        )
        if await self._send(bot, format_slot_alert(link, new_slots)):
            link.notified_keys |= {s.key for s in new_slots}

    async def _send(self, bot: Bot, text: str) -> bool:
        try:
            await bot.send_message(
                chat_id=self._chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            return True
        except Exception:
            logger.exception("Failed to send message")
            return False

    def _apply_updates(self, checked: dict[str, MonitoredLink]) -> None:
        """Persist tracking fields onto freshly loaded state.

        The check cycle takes minutes; reloading before saving avoids
        clobbering /add, /remove or /edit made while it ran.
        """
        state = self._state.load()
        for link in state.links:
            result = checked.get(link.id)
            if result is None or link.url != result.url:
                continue  # link removed or edited mid-cycle — results are stale
            link.notified_keys = set(result.notified_keys)
            link.consecutive_failures = result.consecutive_failures
            link.failure_notified = result.failure_notified
        self._state.save(state)
