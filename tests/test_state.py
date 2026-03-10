import json
from datetime import date, time
from pathlib import Path

from src.models.types import Watch
from src.monitor.state import StateManager


def test_save_and_load(tmp_path: Path):
    state_file = tmp_path / "state.json"
    mgr = StateManager(state_file)

    watch = Watch(
        location_slug="test-centre",
        dates=[date(2026, 3, 15), date(2026, 3, 16)],
        time_start=time(18, 0),
        time_end=time(21, 0),
    )
    mgr.add_watch(watch)

    state = mgr.load()
    assert len(state.watches) == 1
    assert state.watches[0].id == watch.id
    assert state.watches[0].location_slug == "test-centre"
    assert state.watches[0].dates == [date(2026, 3, 15), date(2026, 3, 16)]
    assert state.watches[0].time_start == time(18, 0)


def test_remove_watch(tmp_path: Path):
    state_file = tmp_path / "state.json"
    mgr = StateManager(state_file)

    w1 = Watch(location_slug="a", dates=[date(2026, 3, 15)])
    w2 = Watch(location_slug="b", dates=[date(2026, 3, 16)])
    mgr.add_watch(w1)
    mgr.add_watch(w2)

    assert mgr.remove_watch(w1.id) is True
    assert mgr.remove_watch("nonexistent") is False

    state = mgr.load()
    assert len(state.watches) == 1
    assert state.watches[0].id == w2.id


def test_load_empty(tmp_path: Path):
    state_file = tmp_path / "state.json"
    mgr = StateManager(state_file)
    state = mgr.load()
    assert state.watches == []
    assert state.monitoring_enabled is True


def test_cleanup_expired(tmp_path: Path):
    state_file = tmp_path / "state.json"
    mgr = StateManager(state_file)

    past = Watch(location_slug="old", dates=[date(2020, 1, 1)])
    future = Watch(location_slug="new", dates=[date(2030, 1, 1)])
    mgr.add_watch(past)
    mgr.add_watch(future)

    removed = mgr.cleanup_expired()
    assert removed == 1

    state = mgr.load()
    assert len(state.watches) == 1
    assert state.watches[0].location_slug == "new"
