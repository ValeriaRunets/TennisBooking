"""Parse booking page HTML to extract time slots.

This module is the most fragile part of the system — it depends on the DOM
structure of bookings.better.org.uk. To mitigate this, it uses a 3-level
parsing strategy:

  Level 1: CSS selectors from config/selectors.json
  Level 2: Heuristic DOM search (find elements containing time patterns)
  Level 3: Full page dump for manual inspection (data/debug/)

Selectors can be updated in config/selectors.json without code changes.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import time
from pathlib import Path

from playwright.async_api import ElementHandle, Page

from src.models.types import TimeSlot

logger = logging.getLogger(__name__)

_SELECTORS_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "selectors.json"
_DUMP_PATH = "data/debug/page_dump.html"

# Cached selectors
_selectors: dict | None = None


def load_selectors() -> dict:
    """Load parsing selectors from config/selectors.json."""
    global _selectors
    if _selectors is not None:
        return _selectors
    try:
        raw = _SELECTORS_PATH.read_text(encoding="utf-8")
        _selectors = json.loads(raw)
        logger.debug("Loaded selectors from %s", _SELECTORS_PATH)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load selectors.json (%s), using defaults", exc)
        _selectors = {
            "slot_selectors": [".activity-card", ".slot", ".time-slot", ".booking-slot",
                               "[data-activity]", ".event-card", ".timetable__item"],
            "fallback_selectors": [".card", ".list-group-item", "tr[data-time]", ".schedule-item"],
            "unavailable_classes": ["disabled", "unavailable", "sold-out", "full", "booked"],
            "unavailable_text": ["sold out", "fully booked", "unavailable", "no availability"],
            "time_pattern": r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})",
            "time_pattern_single": r"(\d{1,2}:\d{2})",
            "court_pattern": r"(Court\s*\d+|Pitch\s*\d+)",
            "price_pattern": r"£[\d.]+",
        }
    return _selectors


def _parse_time(text: str) -> time | None:
    """Parse a time string like '18:00'."""
    text = text.strip()
    m = re.match(r"(\d{1,2}):(\d{2})", text)
    if m:
        h, mins = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mins <= 59:
            return time(h, mins)
    return None


async def _extract_slot_from_element(el: ElementHandle, cfg: dict) -> TimeSlot | None:
    """Extract a TimeSlot from a DOM element containing booking info."""
    # Skip hidden elements (CSS display:none, visibility:hidden, etc.)
    try:
        if not await el.is_visible():
            return None
    except Exception:
        pass  # Some element types don't support is_visible; continue parsing

    text = (await el.inner_text()).strip()
    if not text:
        return None

    # Extract time
    time_match = re.search(cfg.get("time_pattern", r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})"), text)
    if not time_match:
        time_match = re.search(cfg.get("time_pattern_single", r"(\d{1,2}:\d{2})"), text)
    if not time_match:
        return None

    start = _parse_time(time_match.group(1))
    end = _parse_time(time_match.group(2)) if time_match.lastindex and time_match.lastindex >= 2 else None
    if not start:
        return None
    if not end:
        end = time(start.hour + 1 if start.hour < 23 else 23, start.minute)

    # Extract court name
    court_pattern = cfg.get("court_pattern", r"(Court\s*\d+|Pitch\s*\d+)")
    court_match = re.search(court_pattern, text, re.IGNORECASE)
    court_name = court_match.group(0) if court_match else "Court"

    # Determine availability
    classes = (await el.get_attribute("class")) or ""
    text_lower = text.lower()
    is_available = True
    explicitly_unavailable = False
    explicitly_available = False

    unavail_classes = cfg.get("unavailable_classes", [])
    if any(kw in classes.lower() for kw in unavail_classes):
        is_available = False
        explicitly_unavailable = True

    unavail_text = cfg.get("unavailable_text", [])
    if any(kw in text_lower for kw in unavail_text):
        is_available = False
        explicitly_unavailable = True

    # Check for FullyBooked component (Better.org.uk specific)
    fully_booked_el = await el.query_selector(
        "[class*='FullyBooked'], [class*='fullyBooked'], "
        "[class*='fully-booked'], [class*='Fully_Booked']"
    )
    if fully_booked_el:
        is_available = False
        explicitly_unavailable = True

    # "0 spaces available" means unavailable
    if re.search(r"\b0\s+spaces?\s+available\b", text_lower):
        is_available = False
        explicitly_unavailable = True
    # "X spaces available" (X > 0) is a strong positive signal
    elif "space available" in text_lower or "spaces available" in text_lower:
        is_available = True
        explicitly_unavailable = False
        explicitly_available = True

    # Find the actual Book button — search all <a>/<button> for one with "book" text
    book_btn = None
    all_btns = await el.query_selector_all("a, button")
    for btn in all_btns:
        btn_txt = (await btn.inner_text()).strip().lower()
        if "book" in btn_txt:
            book_btn = btn
            break
    # Fallback to last button/link if none has "book" text
    if not book_btn and all_btns:
        book_btn = all_btns[-1]

    if book_btn:
        btn_text = (await book_btn.inner_text()).strip().lower()
        btn_disabled = await book_btn.get_attribute("disabled")
        aria_disabled = await book_btn.get_attribute("aria-disabled")
        btn_classes = (await book_btn.get_attribute("class")) or ""

        if btn_disabled is not None or aria_disabled == "true":
            is_available = False
        elif any(kw in btn_classes.lower() for kw in ["disabled", "fully-booked", "fullybooked"]):
            is_available = False
        elif "sold" in btn_text or "full" in btn_text:
            is_available = False
        elif "book" in btn_text and not explicitly_unavailable:
            is_available = True

    # No book button and no explicit availability signal → not bookable
    if not book_btn and not explicitly_available:
        is_available = False

    # Extract price
    price_pattern = cfg.get("price_pattern", r"£[\d.]+")
    price_match = re.search(price_pattern, text)
    price = price_match.group(0) if price_match else None

    # A real booking slot should have at least a price or a book button
    if not price and not book_btn:
        logger.debug("Skipping element with time %s-%s: no price or book button found", start, end)
        return None

    logger.debug(
        "Slot %s-%s %s: available=%s (text_unavail=%s, btn_disabled=%s, aria_disabled=%s)",
        start, end, court_name, is_available,
        explicitly_unavailable,
        (await book_btn.get_attribute("disabled")) is not None if book_btn else "no_btn",
        (await book_btn.get_attribute("aria-disabled")) if book_btn else "no_btn",
    )

    return TimeSlot(
        start_time=start,
        end_time=end,
        court_name=court_name,
        is_available=is_available,
        price=price,
    )


_CHILD_SLOT_SELECTORS = (
    "[class*='ClassCardComponent__Wrap'], "
    "[class*='ClassCardComponent__Row']"
)


async def _try_css_selectors(page: Page, selector_list: list[str], cfg: dict) -> list[TimeSlot]:
    """Level 1: Try CSS selectors to find slot elements."""
    combined = ", ".join(selector_list)
    elements = await page.query_selector_all(combined)
    if not elements:
        return []

    time_pattern = cfg.get("time_pattern", r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})")
    slots: list[TimeSlot] = []
    seen: set[str] = set()

    for el in elements:
        # Detect wrapper elements that contain multiple time slots
        text = (await el.inner_text()).strip()
        time_count = len(re.findall(time_pattern, text))

        if time_count > 1:
            # Likely a list wrapper — try to find individual slot children
            children = await el.query_selector_all(_CHILD_SLOT_SELECTORS)
            if children:
                logger.debug(
                    "Wrapper element with %d time patterns → splitting into %d children",
                    time_count, len(children),
                )
                for child in children:
                    slot = await _extract_slot_from_element(child, cfg)
                    if slot and slot.key not in seen:
                        seen.add(slot.key)
                        slots.append(slot)
                continue

        # Single slot element
        slot = await _extract_slot_from_element(el, cfg)
        if slot and slot.key not in seen:
            seen.add(slot.key)
            slots.append(slot)

    return slots


# JavaScript to find DOM containers that contain time patterns
_HEURISTIC_JS = """
() => {
    const timeRe = /\\d{1,2}:\\d{2}/;
    const priceRe = /£/;
    const bookRe = /book/i;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const containers = new Set();
    while (walker.nextNode()) {
        const txt = walker.currentNode.textContent.trim();
        if (txt && timeRe.test(txt)) {
            let el = walker.currentNode.parentElement;
            let candidate = null;
            let depth = 0;
            while (el && el !== document.body && depth < 15) {
                const tag = el.tagName.toLowerCase();
                // Accept any semantic container, or divs/spans with content
                if (['li', 'tr', 'article', 'section', 'a'].includes(tag) ||
                    (tag === 'div' && el.children.length >= 1) ||
                    (tag === 'div' && el.textContent.length > 20)) {
                    candidate = el;
                    // Stop at a container with price or booking info
                    const content = el.textContent;
                    if (priceRe.test(content) || bookRe.test(content)) {
                        break;
                    }
                }
                el = el.parentElement;
                depth++;
            }
            if (candidate) containers.add(candidate);
        }
    }
    // Tag each container with a data attribute for later querySelector
    let idx = 0;
    const result = [];
    for (const c of containers) {
        const attr = `data-heuristic-slot-${idx}`;
        c.setAttribute(attr, '1');
        result.push(attr);
        idx++;
    }
    return result;
}
"""


async def _try_heuristic_search(page: Page, cfg: dict) -> list[TimeSlot]:
    """Level 2: Heuristic search — find elements containing time patterns via JS TreeWalker."""
    try:
        attrs = await page.evaluate(_HEURISTIC_JS)
    except Exception:
        logger.exception("Heuristic JS failed")
        return []

    if not attrs:
        return []

    logger.info("Heuristic search found %d candidate containers", len(attrs))

    slots: list[TimeSlot] = []
    seen: set[str] = set()
    for attr in attrs:
        el = await page.query_selector(f"[{attr}]")
        if not el:
            continue
        slot = await _extract_slot_from_element(el, cfg)
        if slot and slot.key not in seen:
            seen.add(slot.key)
            slots.append(slot)

    return slots


async def parse_availability(page: Page) -> list[TimeSlot]:
    """Extract time slots from a Better booking 'by-time' page.

    Uses a 3-level strategy:
      1. CSS selectors from selectors.json
      2. Heuristic DOM search (TreeWalker for time patterns)
      3. Page dump for manual inspection
    """
    cfg = load_selectors()

    # Level 1: primary CSS selectors
    slots = await _try_css_selectors(page, cfg.get("slot_selectors", []), cfg)
    if slots:
        logger.info("Level 1 (CSS selectors): found %d slots (%d available)",
                     len(slots), sum(1 for s in slots if s.is_available))
        return slots

    # Level 1b: fallback CSS selectors
    slots = await _try_css_selectors(page, cfg.get("fallback_selectors", []), cfg)
    if slots:
        logger.info("Level 1b (fallback selectors): found %d slots (%d available)",
                     len(slots), sum(1 for s in slots if s.is_available))
        return slots

    # Level 2: heuristic search
    slots = await _try_heuristic_search(page, cfg)
    if slots:
        logger.info("Level 2 (heuristic): found %d slots (%d available)",
                     len(slots), sum(1 for s in slots if s.is_available))
        return slots

    # Level 3: nothing found — dump page for debugging
    html = await page.content()
    time_count = len(re.findall(r"\d{1,2}:\d{2}", html))
    logger.warning(
        "No slots found by any method. Page has %d time patterns in raw HTML. "
        "The page structure may have changed. Dumping HTML for inspection.",
        time_count,
    )
    await dump_page_html(page)
    return []


async def dump_page_html(page: Page, filepath: str = _DUMP_PATH) -> str:
    """Save current page HTML and log basic analysis."""
    html = await page.content()
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    Path(filepath).write_text(html, encoding="utf-8")
    logger.info("Page HTML dumped to %s (%d bytes)", filepath, len(html))

    # Quick analysis
    time_count = len(re.findall(r"\d{1,2}:\d{2}", html))
    price_count = len(re.findall(r"£[\d.]+", html))
    book_count = html.lower().count("book")
    logger.info("Quick analysis: %d time patterns, %d prices, %d 'book' occurrences",
                time_count, price_count, book_count)

    return filepath
