from datetime import date, time

from src.models.types import AppState, Location, TimeSlot, Watch


def test_location_url():
    loc = Location(
        slug="islington-tennis-centre",
        display_name="Islington Tennis Centre",
        activity_slug="highbury-tennis",
    )
    url = loc.url_for_date(date(2026, 3, 15))
    assert url == (
        "https://bookings.better.org.uk/location/"
        "islington-tennis-centre/highbury-tennis/2026-03-15/by-time"
    )


def test_timeslot_key():
    slot = TimeSlot(
        start_time=time(18, 0),
        end_time=time(19, 0),
        court_name="Court 1",
        is_available=True,
    )
    assert slot.key == "18:00-Court 1"


def test_watch_matches_slot():
    watch = Watch(
        location_slug="test",
        dates=[date(2026, 3, 15)],
        time_start=time(18, 0),
        time_end=time(21, 0),
    )
    available = TimeSlot(time(19, 0), time(20, 0), "Court 1", True)
    unavailable = TimeSlot(time(19, 0), time(20, 0), "Court 1", False)
    too_early = TimeSlot(time(17, 0), time(18, 0), "Court 1", True)
    too_late = TimeSlot(time(21, 0), time(22, 0), "Court 1", True)

    assert watch.matches_slot(available) is True
    assert watch.matches_slot(unavailable) is False
    assert watch.matches_slot(too_early) is False
    assert watch.matches_slot(too_late) is False


def test_watch_matches_any_time():
    watch = Watch(location_slug="test", dates=[date(2026, 3, 15)])
    slot = TimeSlot(time(6, 0), time(7, 0), "Court 1", True)
    assert watch.matches_slot(slot) is True


def test_watch_short_description():
    watch = Watch(
        location_slug="test-centre",
        dates=[date(2026, 3, 15), date(2026, 3, 16)],
        time_start=time(18, 0),
        time_end=time(21, 0),
    )
    desc = watch.short_description
    assert "test-centre" in desc
    assert "18:00-21:00" in desc
