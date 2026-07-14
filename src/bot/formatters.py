"""Format data for Telegram messages."""

from __future__ import annotations

from src.models.types import MonitoredLink, TimeSlot


def format_link(link: MonitoredLink, index: int = 0) -> str:
    name = link.label or link.url
    if len(name) > 70:
        name = name[:67] + "..."
    status = "active" if link.active else "paused"
    return (
        f"{index}. {name}\n"
        f"   Time: <b>{link.time_description}</b> | Status: {status}\n"
        f"   ID: <code>{link.id}</code>"
    )


def format_link_list(links: list[MonitoredLink]) -> str:
    if not links:
        return "No monitored links. Use /add to add one."
    lines = ["<b>Monitored links:</b>\n"]
    for i, link in enumerate(links, 1):
        lines.append(format_link(link, i))
        lines.append("")
    return "\n".join(lines)


def format_parse_failure_warning(link: MonitoredLink) -> str:
    name = link.label or link.url
    return (
        f"⚠️ <b>Trouble checking a link</b>\n"
        f"📍 {name}\n\n"
        f"The last few checks found no slots at all. The page structure may "
        f"have changed, or the date in the URL may have passed.\n\n"
        f"Update the link's URL to a fresh page (link id: <code>{link.id}</code>) — "
        f"via /edit if the bot is running, or by editing data/state.json "
        f"if deployed on GitHub Actions."
    )


def format_slot_alert(link: MonitoredLink, matching_slots: list[TimeSlot]) -> str:
    name = link.label or "Link"
    lines = [
        f"🔔 <b>Courts available! ({link.time_description})</b>\n"
        f"📍 {name}\n"
    ]
    for slot in matching_slots:
        price_str = f" ({slot.price})" if slot.price else ""
        lines.append(
            f"  ✅ {slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')} "
            f"{slot.court_name}{price_str}"
        )
    lines.append(f"\n<a href=\"{link.url}\">Book now →</a>")
    return "\n".join(lines)
