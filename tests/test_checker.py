"""Tests for src.monitor.checker — alert dedup and parse-failure warnings."""

from __future__ import annotations

from datetime import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.types import MonitoredLink, TimeSlot
from src.monitor.checker import FAILURE_ALERT_THRESHOLD, AvailabilityChecker
from src.monitor.state import StateManager

URL = "https://bookings.better.org.uk/location/test/tennis/2026-03-15/by-time"


def _slot(hour: int, court: str = "Court 1", available: bool = True) -> TimeSlot:
    return TimeSlot(
        start_time=time(hour, 0),
        end_time=time(hour + 1, 0),
        court_name=court,
        is_available=available,
        price="£5.50",
    )


def _make_checker(tmp_path: Path, links: list[MonitoredLink], slots_by_url: dict):
    """Build a checker over a real StateManager and a mocked fetcher/bot.

    `slots_by_url` is read on every cycle, so tests can mutate it between
    calls to simulate slots appearing and disappearing.
    """
    mgr = StateManager(tmp_path / "state.json")
    for link in links:
        mgr.add_link(link)

    fetcher = MagicMock()

    async def _fetch_multiple(urls, *args, **kwargs):
        return {u: list(slots_by_url.get(u, [])) for u in urls}

    fetcher.fetch_multiple = AsyncMock(side_effect=_fetch_multiple)

    checker = AvailabilityChecker(fetcher, mgr, chat_id=123)
    context = MagicMock()
    context.bot.send_message = AsyncMock()
    return checker, mgr, context


@pytest.mark.asyncio
async def test_alert_sent_for_new_slot(tmp_path):
    link = MonitoredLink(url=URL, time_start=time(18, 0), time_end=time(21, 0))
    slots = {URL: [_slot(18)]}
    checker, _, context = _make_checker(tmp_path, [link], slots)

    await checker.check_all_links(context)

    context.bot.send_message.assert_awaited_once()
    assert "18:00" in context.bot.send_message.call_args.kwargs["text"]


@pytest.mark.asyncio
async def test_no_duplicate_alert_while_slot_stays_available(tmp_path):
    link = MonitoredLink(url=URL)
    slots = {URL: [_slot(18)]}
    checker, _, context = _make_checker(tmp_path, [link], slots)

    await checker.check_all_links(context)
    await checker.check_all_links(context)
    await checker.check_all_links(context)

    assert context.bot.send_message.await_count == 1


@pytest.mark.asyncio
async def test_alert_again_after_slot_disappears_and_returns(tmp_path):
    link = MonitoredLink(url=URL)
    slots = {URL: [_slot(18)]}
    checker, _, context = _make_checker(tmp_path, [link], slots)

    await checker.check_all_links(context)  # alert
    slots[URL] = [_slot(18, available=False)]  # someone booked it
    await checker.check_all_links(context)  # no alert
    slots[URL] = [_slot(18)]  # it freed up again
    await checker.check_all_links(context)  # alert again

    assert context.bot.send_message.await_count == 2


@pytest.mark.asyncio
async def test_only_new_slots_in_second_alert(tmp_path):
    link = MonitoredLink(url=URL)
    slots = {URL: [_slot(18)]}
    checker, _, context = _make_checker(tmp_path, [link], slots)

    await checker.check_all_links(context)
    slots[URL] = [_slot(18), _slot(19, court="Court 2")]
    await checker.check_all_links(context)

    assert context.bot.send_message.await_count == 2
    second_msg = context.bot.send_message.call_args.kwargs["text"]
    assert "19:00" in second_msg
    assert "18:00" not in second_msg


@pytest.mark.asyncio
async def test_unavailable_slots_no_alert(tmp_path):
    link = MonitoredLink(url=URL)
    slots = {URL: [_slot(18, available=False), _slot(19, available=False)]}
    checker, _, context = _make_checker(tmp_path, [link], slots)

    await checker.check_all_links(context)

    context.bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_notified_keys_persisted(tmp_path):
    link = MonitoredLink(url=URL)
    slots = {URL: [_slot(18)]}
    checker, mgr, context = _make_checker(tmp_path, [link], slots)

    await checker.check_all_links(context)

    saved = mgr.load().links[0]
    assert saved.notified_keys == {_slot(18).key}


@pytest.mark.asyncio
async def test_failure_warning_after_threshold_sent_once(tmp_path):
    link = MonitoredLink(url=URL)
    slots = {URL: []}
    checker, mgr, context = _make_checker(tmp_path, [link], slots)

    for _ in range(FAILURE_ALERT_THRESHOLD + 3):
        await checker.check_all_links(context)

    assert context.bot.send_message.await_count == 1
    assert "Trouble" in context.bot.send_message.call_args.kwargs["text"]
    saved = mgr.load().links[0]
    assert saved.failure_notified is True
    assert saved.consecutive_failures == FAILURE_ALERT_THRESHOLD + 3


@pytest.mark.asyncio
async def test_failure_counter_resets_on_success(tmp_path):
    link = MonitoredLink(url=URL)
    slots = {URL: []}
    checker, mgr, context = _make_checker(tmp_path, [link], slots)

    for _ in range(FAILURE_ALERT_THRESHOLD - 1):
        await checker.check_all_links(context)
    slots[URL] = [_slot(18, available=False)]  # page parses again
    await checker.check_all_links(context)

    context.bot.send_message.assert_not_awaited()
    saved = mgr.load().links[0]
    assert saved.consecutive_failures == 0


@pytest.mark.asyncio
async def test_link_added_mid_cycle_survives_save(tmp_path):
    """A /add issued while the check cycle runs must not be clobbered."""
    link = MonitoredLink(url=URL)
    slots = {URL: [_slot(18)]}
    checker, mgr, context = _make_checker(tmp_path, [link], slots)

    added_mid_cycle = MonitoredLink(url="https://example.com/other")

    original_fetch = checker._fetcher.fetch_multiple

    async def _fetch_and_add(urls, *args, **kwargs):
        mgr.add_link(added_mid_cycle)  # simulates a concurrent /add
        return await original_fetch(urls, *args, **kwargs)

    checker._fetcher.fetch_multiple = AsyncMock(side_effect=_fetch_and_add)

    await checker.check_all_links(context)

    saved_ids = {l.id for l in mgr.load().links}
    assert added_mid_cycle.id in saved_ids


@pytest.mark.asyncio
async def test_paused_monitoring_skips_checks(tmp_path):
    link = MonitoredLink(url=URL)
    slots = {URL: [_slot(18)]}
    checker, mgr, context = _make_checker(tmp_path, [link], slots)

    state = mgr.load()
    state.monitoring_enabled = False
    mgr.save(state)

    await checker.check_all_links(context)

    context.bot.send_message.assert_not_awaited()
    checker._fetcher.fetch_multiple.assert_not_awaited()
