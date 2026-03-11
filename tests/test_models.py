from datetime import time

from src.models.types import AppState, MonitoredLink, TimeSlot


def test_timeslot_key():
    slot = TimeSlot(
        start_time=time(18, 0),
        end_time=time(19, 0),
        court_name="Court 1",
        is_available=True,
    )
    assert slot.key == "18:00-Court 1"


def test_matches_slot_in_range():
    link = MonitoredLink(
        url="https://example.com",
        time_start=time(18, 0),
        time_end=time(21, 0),
    )
    available = TimeSlot(time(19, 0), time(20, 0), "Court 1", True)
    unavailable = TimeSlot(time(19, 0), time(20, 0), "Court 1", False)
    too_early = TimeSlot(time(17, 0), time(18, 0), "Court 1", True)
    too_late = TimeSlot(time(21, 0), time(22, 0), "Court 1", True)

    assert link.matches_slot(available) is True
    assert link.matches_slot(unavailable) is False
    assert link.matches_slot(too_early) is False
    assert link.matches_slot(too_late) is False


def test_matches_slot_any_time():
    link = MonitoredLink(url="https://example.com")
    slot = TimeSlot(time(6, 0), time(7, 0), "Court 1", True)
    assert link.matches_slot(slot) is True


def test_time_description_range():
    link = MonitoredLink(url="https://example.com", time_start=time(18, 0), time_end=time(21, 0))
    assert link.time_description == "18:00-21:00"


def test_time_description_any():
    link = MonitoredLink(url="https://example.com")
    assert link.time_description == "any time"


def test_short_description():
    link = MonitoredLink(url="https://example.com", time_start=time(18, 0), time_end=time(21, 0), label="Islington")
    assert "Islington" in link.short_description
    assert "18:00-21:00" in link.short_description


def test_app_state_defaults():
    state = AppState()
    assert state.links == []
    assert state.monitoring_enabled is True
