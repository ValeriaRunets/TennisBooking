"""Format data for Telegram messages."""

from __future__ import annotations

from src.models.types import AvailabilitySnapshot, Location, TimeSlot, Watch


def format_watch(watch: Watch, locations: dict[str, Location]) -> str:
    loc = locations.get(watch.location_slug)
    name = loc.display_name if loc else watch.location_slug
    return (
        f"🎾 <b>{name}</b>\n"
        f"   {watch.short_description}\n"
        f"   ID: <code>{watch.id}</code>"
    )


def format_watch_list(watches: list[Watch], locations: dict[str, Location]) -> str:
    if not watches:
        return "No active watches. Use /watch to add one."
    lines = ["<b>Active watches:</b>\n"]
    for i, w in enumerate(watches, 1):
        lines.append(f"{i}. {format_watch(w, locations)}\n")
    return "\n".join(lines)


def format_availability(snapshot: AvailabilitySnapshot, location: Location) -> str:
    available = snapshot.available_slots
    if not available:
        return (
            f"<b>{location.display_name}</b> — {snapshot.query_date.isoformat()}\n"
            f"No available slots."
        )
    lines = [
        f"<b>{location.display_name}</b> — {snapshot.query_date.isoformat()}\n"
        f"Available slots ({len(available)}):\n"
    ]
    for slot in available:
        price_str = f" ({slot.price})" if slot.price else ""
        lines.append(
            f"  ✅ {slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')} "
            f"{slot.court_name}{price_str}"
        )
    return "\n".join(lines)


def format_new_slots_alert(
    location: Location,
    query_date: str,
    new_slots: list[TimeSlot],
) -> str:
    lines = [
        f"🔔 <b>New courts available!</b>\n"
        f"📍 {location.display_name} — {query_date}\n"
    ]
    for slot in new_slots:
        price_str = f" ({slot.price})" if slot.price else ""
        lines.append(
            f"  ✅ {slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')} "
            f"{slot.court_name}{price_str}"
        )
    url = location.url_for_date(
        __import__("datetime").date.fromisoformat(query_date)
    )
    lines.append(f"\n<a href=\"{url}\">Book now →</a>")
    return "\n".join(lines)


def format_locations(locations: dict[str, Location]) -> str:
    if not locations:
        return "No locations configured."
    lines = ["<b>Available locations:</b>\n"]
    for slug, loc in locations.items():
        lines.append(f"  • <b>{loc.display_name}</b> (<code>{slug}</code>)")
    return "\n".join(lines)
