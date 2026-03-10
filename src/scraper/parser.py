"""Parse booking page HTML to extract time slots.

This module is the most fragile part of the system — it depends on the DOM
structure of bookings.better.org.uk. If the site changes its layout, the
CSS selectors below will need updating.

The selectors were designed based on common patterns found on Better booking
pages. On first run, use `dump_page_html()` to save the actual page HTML and
refine selectors as needed.
"""

from __future__ import annotations

import logging
import re
from datetime import time
from pathlib import Path

from playwright.async_api import Page

from src.models.types import TimeSlot

logger = logging.getLogger(__name__)


async def dump_page_html(page: Page, filepath: str = "tests/fixtures/sample_page.html") -> None:
    """Save current page HTML for offline debugging."""
    html = await page.content()
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    Path(filepath).write_text(html, encoding="utf-8")
    logger.info("Page HTML dumped to %s", filepath)


def _parse_time(text: str) -> time | None:
    """Parse a time string like '18:00' or '6:00 PM'."""
    text = text.strip()
    # Try HH:MM
    m = re.match(r"(\d{1,2}):(\d{2})", text)
    if m:
        return time(int(m.group(1)), int(m.group(2)))
    return None


async def parse_availability(page: Page) -> list[TimeSlot]:
    """Extract time slots from a Better booking 'by-time' page.

    Strategy: look for slot elements that contain time, court name, and
    availability indicators. The selectors below try multiple common patterns
    and fall back gracefully.
    """
    slots: list[TimeSlot] = []

    # Try to find slot containers — adjust selectors based on actual DOM
    # Pattern 1: table-based layout with rows per time slot
    slot_elements = await page.query_selector_all(
        ".activity-card, .slot, .time-slot, .booking-slot, "
        "[data-activity], .event-card, .timetable__item"
    )

    if not slot_elements:
        # Pattern 2: try broader selectors
        slot_elements = await page.query_selector_all(
            ".card, .list-group-item, tr[data-time], .schedule-item"
        )

    if not slot_elements:
        logger.warning(
            "No slot elements found on page. The page structure may have changed. "
            "Use dump_page_html() to inspect."
        )
        # Dump page for debugging
        await dump_page_html(page)
        return slots

    for el in slot_elements:
        text = (await el.inner_text()).strip()
        if not text:
            continue

        # Try to extract time from the element text
        time_match = re.search(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})", text)
        if not time_match:
            time_match = re.search(r"(\d{1,2}:\d{2})", text)

        if not time_match:
            continue

        start = _parse_time(time_match.group(1))
        end = _parse_time(time_match.group(2)) if time_match.lastindex and time_match.lastindex >= 2 else None
        if not start:
            continue
        if not end:
            end = time(start.hour + 1, start.minute)  # default 1h slot

        # Try to extract court name
        court_match = re.search(r"(Court\s*\d+|Pitch\s*\d+)", text, re.IGNORECASE)
        court_name = court_match.group(0) if court_match else "Court"

        # Determine availability
        classes = (await el.get_attribute("class")) or ""
        is_available = True

        # Check for unavailability indicators
        unavail_keywords = ["disabled", "unavailable", "sold-out", "full", "booked"]
        if any(kw in classes.lower() for kw in unavail_keywords):
            is_available = False
        if any(kw in text.lower() for kw in ["sold out", "fully booked", "unavailable", "no availability"]):
            is_available = False

        # Check for book button as positive availability signal
        book_btn = await el.query_selector("a, button")
        if book_btn:
            btn_text = (await book_btn.inner_text()).strip().lower()
            if "book" in btn_text:
                is_available = True
            elif "sold" in btn_text or "full" in btn_text:
                is_available = False

        # Try to extract price
        price_match = re.search(r"£[\d.]+", text)
        price = price_match.group(0) if price_match else None

        slots.append(
            TimeSlot(
                start_time=start,
                end_time=end,
                court_name=court_name,
                is_available=is_available,
                price=price,
            )
        )

    logger.info("Parsed %d slots (%d available)", len(slots), sum(1 for s in slots if s.is_available))
    return slots
