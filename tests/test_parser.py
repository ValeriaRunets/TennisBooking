"""Tests for src.scraper.parser — adaptive 3-level parsing."""

from __future__ import annotations

import json
from datetime import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.scraper.parser import (
    _extract_slot_from_element,
    _try_css_selectors,
    _try_heuristic_search,
    load_selectors,
    parse_availability,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_element(
    text: str,
    classes: str = "",
    btn_text: str | None = None,
    btn_disabled: bool = False,
    has_fully_booked_el: bool = False,
) -> AsyncMock:
    """Create a mock Playwright ElementHandle."""
    el = AsyncMock()
    el.inner_text = AsyncMock(return_value=text)
    el.get_attribute = AsyncMock(return_value=classes)

    # Build button mock
    btn = None
    if btn_text is not None:
        btn = AsyncMock()
        btn.inner_text = AsyncMock(return_value=btn_text)
        btn.get_attribute = AsyncMock(
            return_value="" if btn_disabled else None
        )

    # Build FullyBooked element mock
    fully_booked_mock = AsyncMock() if has_fully_booked_el else None

    # query_selector is called twice: first for "[class*='FullyBooked']", then for "a, button"
    async def _query_selector(selector):
        if "FullyBooked" in selector:
            return fully_booked_mock
        if selector == "a, button":
            return btn
        return None

    el.query_selector = _query_selector
    return el


def _mock_page(elements: list[AsyncMock] | None = None, evaluate_results=None) -> AsyncMock:
    """Create a mock Playwright Page."""
    page = AsyncMock()
    page.query_selector_all = AsyncMock(return_value=elements or [])
    page.query_selector = AsyncMock(return_value=None)
    page.content = AsyncMock(return_value="<html><body></body></html>")

    if evaluate_results is not None:
        page.evaluate = AsyncMock(side_effect=evaluate_results)
    else:
        page.evaluate = AsyncMock(return_value=[])

    return page


@pytest.fixture(autouse=True)
def _reset_selectors_cache():
    """Reset the cached selectors before each test."""
    import src.scraper.parser as mod
    mod._selectors = None
    yield
    mod._selectors = None


# ---------------------------------------------------------------------------
# load_selectors
# ---------------------------------------------------------------------------

def test_load_selectors_returns_dict():
    cfg = load_selectors()
    assert isinstance(cfg, dict)
    assert "slot_selectors" in cfg
    assert "unavailable_classes" in cfg
    assert "time_pattern" in cfg


def test_load_selectors_caches():
    cfg1 = load_selectors()
    cfg2 = load_selectors()
    assert cfg1 is cfg2


def test_load_selectors_fallback_on_missing_file():
    import src.scraper.parser as mod
    mod._selectors = None
    original = mod._SELECTORS_PATH
    mod._SELECTORS_PATH = original.parent / "nonexistent.json"
    try:
        cfg = load_selectors()
        assert "slot_selectors" in cfg
    finally:
        mod._SELECTORS_PATH = original
        mod._selectors = None


# ---------------------------------------------------------------------------
# _extract_slot_from_element
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_slot_with_time_range():
    cfg = load_selectors()
    el = _mock_element("18:00 - 19:00 Court 1 £5.50", btn_text="Book")
    slot = await _extract_slot_from_element(el, cfg)
    assert slot is not None
    assert slot.start_time == time(18, 0)
    assert slot.end_time == time(19, 0)
    assert slot.court_name == "Court 1"
    assert slot.is_available is True
    assert slot.price == "£5.50"


@pytest.mark.asyncio
async def test_extract_slot_single_time():
    cfg = load_selectors()
    el = _mock_element("18:00 Court 2")
    slot = await _extract_slot_from_element(el, cfg)
    assert slot is not None
    assert slot.start_time == time(18, 0)
    assert slot.end_time == time(19, 0)  # default +1h
    assert slot.court_name == "Court 2"


@pytest.mark.asyncio
async def test_extract_slot_unavailable_class():
    cfg = load_selectors()
    el = _mock_element("18:00 - 19:00 Court 1", classes="slot disabled")
    slot = await _extract_slot_from_element(el, cfg)
    assert slot is not None
    assert slot.is_available is False


@pytest.mark.asyncio
async def test_extract_slot_unavailable_text():
    cfg = load_selectors()
    el = _mock_element("18:00 - 19:00 Court 1 Sold Out")
    slot = await _extract_slot_from_element(el, cfg)
    assert slot is not None
    assert slot.is_available is False


@pytest.mark.asyncio
async def test_extract_slot_sold_out_button():
    cfg = load_selectors()
    el = _mock_element("18:00 - 19:00 Court 1", btn_text="Sold Out")
    slot = await _extract_slot_from_element(el, cfg)
    assert slot is not None
    assert slot.is_available is False


@pytest.mark.asyncio
async def test_extract_slot_fully_booked_with_book_button():
    """Fully booked text + disabled 'Book' button → unavailable (regression test)."""
    cfg = load_selectors()
    el = _mock_element(
        "08:00 - 09:00 60min Highbury Fields Tennis £12.35 Fully booked Book",
        btn_text="Book",
        btn_disabled=True,
        has_fully_booked_el=True,
    )
    slot = await _extract_slot_from_element(el, cfg)
    assert slot is not None
    assert slot.start_time == time(8, 0)
    assert slot.is_available is False


@pytest.mark.asyncio
async def test_extract_slot_spaces_available():
    """'X spaces available' text → available."""
    cfg = load_selectors()
    el = _mock_element(
        "09:00 - 10:00 60min Highbury Fields Tennis £12.35 2 spaces available",
        btn_text="Book",
    )
    slot = await _extract_slot_from_element(el, cfg)
    assert slot is not None
    assert slot.start_time == time(9, 0)
    assert slot.is_available is True


@pytest.mark.asyncio
async def test_extract_slot_disabled_button():
    """Disabled button → unavailable even without explicit text."""
    cfg = load_selectors()
    el = _mock_element(
        "18:00 - 19:00 Court 1 £5.50",
        btn_text="Book",
        btn_disabled=True,
    )
    slot = await _extract_slot_from_element(el, cfg)
    assert slot is not None
    assert slot.is_available is False


@pytest.mark.asyncio
async def test_extract_slot_no_time():
    cfg = load_selectors()
    el = _mock_element("No time info here")
    slot = await _extract_slot_from_element(el, cfg)
    assert slot is None


@pytest.mark.asyncio
async def test_extract_slot_empty_text():
    cfg = load_selectors()
    el = _mock_element("")
    slot = await _extract_slot_from_element(el, cfg)
    assert slot is None


# ---------------------------------------------------------------------------
# _try_css_selectors
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_try_css_selectors_finds_slots():
    cfg = load_selectors()
    el1 = _mock_element("18:00 - 19:00 Court 1 £5.50", btn_text="Book")
    el2 = _mock_element("19:00 - 20:00 Court 2 £5.50", btn_text="Book")
    page = _mock_page([el1, el2])

    slots = await _try_css_selectors(page, [".slot", ".time-slot"], cfg)
    assert len(slots) == 2
    assert slots[0].start_time == time(18, 0)
    assert slots[1].start_time == time(19, 0)


@pytest.mark.asyncio
async def test_try_css_selectors_empty():
    cfg = load_selectors()
    page = _mock_page([])
    slots = await _try_css_selectors(page, [".slot"], cfg)
    assert slots == []


# ---------------------------------------------------------------------------
# _try_heuristic_search
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_try_heuristic_finds_containers():
    cfg = load_selectors()

    # Simulate JS returning data attributes
    page = AsyncMock()
    page.evaluate = AsyncMock(return_value=["data-heuristic-slot-0", "data-heuristic-slot-1"])

    el1 = _mock_element("18:00 - 19:00 Court 1 £5.50", btn_text="Book")
    el2 = _mock_element("20:00 - 21:00 Court 2", btn_text="Book")

    call_count = 0
    async def mock_query_selector(selector):
        nonlocal call_count
        result = [el1, el2][call_count] if call_count < 2 else None
        call_count += 1
        return result

    page.query_selector = mock_query_selector

    slots = await _try_heuristic_search(page, cfg)
    assert len(slots) == 2


@pytest.mark.asyncio
async def test_try_heuristic_empty():
    cfg = load_selectors()
    page = AsyncMock()
    page.evaluate = AsyncMock(return_value=[])
    slots = await _try_heuristic_search(page, cfg)
    assert slots == []


# ---------------------------------------------------------------------------
# parse_availability — integration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parse_availability_level1():
    """Level 1 CSS selectors find slots → returns them."""
    el = _mock_element("18:00 - 19:00 Court 1 £5.50", btn_text="Book")
    page = _mock_page([el])

    slots = await parse_availability(page)
    assert len(slots) == 1
    assert slots[0].start_time == time(18, 0)
    assert slots[0].is_available is True


@pytest.mark.asyncio
async def test_parse_availability_falls_to_heuristic():
    """Level 1 returns nothing → falls through to heuristic."""
    page = AsyncMock()

    # First two calls (level 1, level 1b) return empty
    css_call_count = 0
    async def mock_query_selector_all(selector):
        nonlocal css_call_count
        css_call_count += 1
        return []
    page.query_selector_all = mock_query_selector_all

    # Heuristic returns one container
    page.evaluate = AsyncMock(return_value=["data-heuristic-slot-0"])
    el = _mock_element("20:00 - 21:00 Court 3 £6.00", btn_text="Book")
    page.query_selector = AsyncMock(return_value=el)

    slots = await parse_availability(page)
    assert len(slots) == 1
    assert slots[0].court_name == "Court 3"


@pytest.mark.asyncio
async def test_parse_availability_empty_dumps_html(tmp_path):
    """No slots found → dumps HTML."""
    page = AsyncMock()
    page.query_selector_all = AsyncMock(return_value=[])
    page.evaluate = AsyncMock(return_value=[])
    page.content = AsyncMock(return_value="<html><body>empty</body></html>")

    dump_path = str(tmp_path / "dump.html")
    with patch("src.scraper.parser.dump_page_html", wraps=None) as mock_dump:
        mock_dump.return_value = dump_path
        slots = await parse_availability(page)

    assert slots == []
    mock_dump.assert_awaited_once()
