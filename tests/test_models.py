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


def test_monitored_link_short_description():
    link = MonitoredLink(
        url="https://example.com/booking",
        desired_time=time(18, 0),
        label="Islington Tuesday",
    )
    desc = link.short_description
    assert "Islington Tuesday" in desc
    assert "18:00" in desc


def test_monitored_link_short_description_no_label():
    link = MonitoredLink(
        url="https://example.com/booking",
        desired_time=time(18, 0),
    )
    desc = link.short_description
    assert "example.com" in desc
    assert "18:00" in desc


def test_app_state_defaults():
    state = AppState()
    assert state.links == []
    assert state.notified == {}
    assert state.monitoring_enabled is True
