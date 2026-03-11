from datetime import time
from pathlib import Path

from src.models.types import MonitoredLink
from src.monitor.state import StateManager


def test_save_and_load(tmp_path: Path):
    state_file = tmp_path / "state.json"
    mgr = StateManager(state_file)

    link = MonitoredLink(
        url="https://bookings.better.org.uk/location/test/tennis/2026-03-15/by-time",
        time_start=time(18, 0),
        time_end=time(21, 0),
        label="Test Court",
    )
    mgr.add_link(link)

    state = mgr.load()
    assert len(state.links) == 1
    assert state.links[0].id == link.id
    assert state.links[0].url == link.url
    assert state.links[0].time_start == time(18, 0)
    assert state.links[0].time_end == time(21, 0)
    assert state.links[0].label == "Test Court"


def test_save_and_load_any_time(tmp_path: Path):
    state_file = tmp_path / "state.json"
    mgr = StateManager(state_file)

    link = MonitoredLink(url="https://example.com")
    mgr.add_link(link)

    state = mgr.load()
    assert state.links[0].time_start is None
    assert state.links[0].time_end is None


def test_remove_link(tmp_path: Path):
    state_file = tmp_path / "state.json"
    mgr = StateManager(state_file)

    l1 = MonitoredLink(url="https://example.com/a", time_start=time(18, 0), time_end=time(20, 0))
    l2 = MonitoredLink(url="https://example.com/b", time_start=time(19, 0), time_end=time(21, 0))
    mgr.add_link(l1)
    mgr.add_link(l2)

    assert mgr.remove_link(l1.id) is True
    assert mgr.remove_link("nonexistent") is False

    state = mgr.load()
    assert len(state.links) == 1
    assert state.links[0].id == l2.id


def test_update_link_time(tmp_path: Path):
    state_file = tmp_path / "state.json"
    mgr = StateManager(state_file)

    link = MonitoredLink(url="https://example.com", time_start=time(18, 0), time_end=time(20, 0))
    mgr.add_link(link)

    # Change to any time
    assert mgr.update_link(link.id, time_start=None, time_end=None) is True
    state = mgr.load()
    assert state.links[0].time_start is None
    assert state.links[0].time_end is None


def test_update_link_label(tmp_path: Path):
    state_file = tmp_path / "state.json"
    mgr = StateManager(state_file)

    link = MonitoredLink(url="https://example.com", label="Old")
    mgr.add_link(link)

    assert mgr.update_link(link.id, label="New Label") is True
    assert mgr.update_link("nonexistent", label="x") is False

    state = mgr.load()
    assert state.links[0].label == "New Label"


def test_load_empty(tmp_path: Path):
    state_file = tmp_path / "state.json"
    mgr = StateManager(state_file)
    state = mgr.load()
    assert state.links == []
    assert state.monitoring_enabled is True
