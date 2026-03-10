"""Core monitoring logic: check watches, diff availability, send alerts."""

from __future__ import annotations

import logging
from datetime import date

from telegram.ext import ContextTypes

from src.bot.formatters import format_new_slots_alert
from src.models.types import AvailabilitySnapshot, Location, TimeSlot, Watch
from src.monitor.state import StateManager
from src.scraper.availability import AvailabilityFetcher

logger = logging.getLogger(__name__)


class AvailabilityChecker:
    def __init__(
        self,
        fetcher: AvailabilityFetcher,
        state: StateManager,
        locations: dict[str, Location],
        chat_id: int,
    ) -> None:
        self._fetcher = fetcher
        self._state = state
        self._locations = locations
        self._chat_id = chat_id

    async def check_all_watches(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        state = self._state.load()
        if not state.monitoring_enabled:
            logger.debug("Monitoring is paused, skipping check")
            return

        # Clean up expired watches
        self._state.cleanup_expired()
        state = self._state.load()

        active_watches = [w for w in state.watches if w.active]
        if not active_watches:
            logger.debug("No active watches")
            return

        # Collect unique (location, date) pairs
        today = date.today()
        pairs: dict[str, tuple[Location, date]] = {}
        for watch in active_watches:
            loc = self._locations.get(watch.location_slug)
            if not loc:
                logger.warning("Unknown location: %s", watch.location_slug)
                continue
            for d in watch.dates:
                if d < today:
                    continue
                key = f"{watch.location_slug}:{d.isoformat()}"
                if key not in pairs:
                    pairs[key] = (loc, d)

        if not pairs:
            logger.debug("No future dates to check")
            return

        logger.info("Checking %d location-date pairs for %d watches", len(pairs), len(active_watches))

        # Fetch all
        snapshots = await self._fetcher.fetch_batch(list(pairs.values()))

        # Process each watch
        for watch in active_watches:
            loc = self._locations.get(watch.location_slug)
            if not loc:
                continue

            for d in watch.dates:
                if d < today:
                    continue
                key = f"{watch.location_slug}:{d.isoformat()}"
                snapshot = snapshots.get(key)
                if not snapshot:
                    continue

                # Filter slots by watch time range
                matching = [s for s in snapshot.slots if watch.matches_slot(s)]

                # Diff against last seen
                last_keys = set(state.last_seen.get(key, []))
                new_slots = [s for s in matching if s.key not in last_keys]

                if new_slots:
                    logger.info(
                        "Found %d new slots for %s on %s",
                        len(new_slots), watch.location_slug, d.isoformat(),
                    )
                    msg = format_new_slots_alert(loc, d.isoformat(), new_slots)
                    try:
                        await context.bot.send_message(
                            chat_id=self._chat_id,
                            text=msg,
                            parse_mode="HTML",
                            disable_web_page_preview=True,
                        )
                    except Exception:
                        logger.exception("Failed to send alert")

                # Update last_seen with ALL currently available matching slots
                state.last_seen[key] = [s.key for s in matching]

        self._state.save(state)
        logger.info("Check cycle complete")
