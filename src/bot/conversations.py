"""Multi-step conversation handler for /watch command."""

from __future__ import annotations

import logging
import re
from datetime import date, time, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.models.types import Location, Watch
from src.monitor.state import StateManager
from src.scraper.locations import load_venue_cache
from src.services.geocoding import find_nearest, geocode_postcode

logger = logging.getLogger(__name__)

ENTER_POSTCODE, SELECT_LOCATION, ENTER_DATES, ENTER_TIMES = range(4)


def _get_locations(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Location]:
    return context.bot_data["locations"]


def _get_state(context: ContextTypes.DEFAULT_TYPE) -> StateManager:
    return context.bot_data["state"]


async def watch_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: ask for postcode."""
    await update.message.reply_text(
        "Enter your UK postcode to find nearby tennis courts\n"
        "(e.g. <code>N1 1AA</code>):",
        parse_mode="HTML",
    )
    return ENTER_POSTCODE


async def postcode_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Geocode postcode and show nearest venues."""
    postcode = update.message.text.strip().upper()

    # Validate basic postcode format
    if not re.match(r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$", postcode):
        await update.message.reply_text(
            "That doesn't look like a valid UK postcode. Please try again\n"
            "(e.g. <code>N1 1AA</code>):",
            parse_mode="HTML",
        )
        return ENTER_POSTCODE

    await update.message.reply_text("Looking up nearby tennis venues...")

    # Geocode the user's postcode
    coords = await geocode_postcode(postcode)
    if not coords:
        await update.message.reply_text(
            "Could not find that postcode. Please check and try again:",
        )
        return ENTER_POSTCODE

    # Load venue cache
    cached = load_venue_cache()
    if not cached:
        # Fall back to locations already in bot_data
        locations = _get_locations(context)
        cached = [
            {
                "slug": loc.slug,
                "display_name": loc.display_name,
                "activity_slug": loc.activity_slug,
                "postcode": loc.postcode,
                "lat": loc.lat,
                "lon": loc.lon,
            }
            for loc in locations.values()
        ]

    # Filter venues that have coordinates
    venues_with_coords = [v for v in cached if v.get("lat") is not None]

    if not venues_with_coords:
        # If no geocoded venues, show all venues without distance
        await update.message.reply_text(
            "No geocoded venues available. Showing all known locations:"
        )
        locations = _get_locations(context)
        buttons = [
            [InlineKeyboardButton(loc.display_name, callback_data=f"loc:{slug}")]
            for slug, loc in locations.items()
        ]
        await update.message.reply_text(
            "Select a location:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return SELECT_LOCATION

    # Find nearest venues
    nearest = find_nearest(coords, venues_with_coords, n=10)

    # Store nearest venues in user_data for the callback
    context.user_data["nearest_venues"] = nearest

    # Build keyboard
    buttons = []
    for v in nearest:
        label = f"{v['display_name']} ({v['distance_km']} km)"
        # Truncate if too long for Telegram callback button
        if len(label) > 60:
            label = label[:57] + "..."
        buttons.append(
            [InlineKeyboardButton(label, callback_data=f"loc:{v['slug']}")]
        )

    await update.message.reply_text(
        f"Nearest tennis venues to <b>{postcode}</b>:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML",
    )
    return SELECT_LOCATION


async def location_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle location selection, ask for dates."""
    query = update.callback_query
    await query.answer()
    slug = query.data.replace("loc:", "")
    context.user_data["watch_location"] = slug

    # Ensure the selected venue is in bot_data["locations"]
    locations = _get_locations(context)
    if slug not in locations:
        # Add it dynamically from nearest_venues
        nearest = context.user_data.get("nearest_venues", [])
        for v in nearest:
            if v["slug"] == slug:
                locations[slug] = Location(
                    slug=v["slug"],
                    display_name=v["display_name"],
                    activity_slug=v["activity_slug"],
                    postcode=v.get("postcode"),
                    lat=v.get("lat"),
                    lon=v.get("lon"),
                )
                break

    loc = locations.get(slug)
    name = loc.display_name if loc else slug

    await query.edit_message_text(
        f"\U0001f4cd <b>{name}</b>\n\n"
        "Enter date(s) to monitor:\n"
        "  \u2022 Single date: <code>2026-03-15</code>\n"
        "  \u2022 Range: <code>2026-03-15 to 2026-03-20</code>\n"
        "  \u2022 Multiple: <code>2026-03-15, 2026-03-17</code>",
        parse_mode="HTML",
    )
    return ENTER_DATES


async def dates_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parse dates, ask for time range."""
    text = update.message.text.strip()
    dates: list[date] = []

    try:
        if " to " in text or " - " in text:
            parts = re.split(r"\s+to\s+|\s+-\s+", text)
            start = date.fromisoformat(parts[0].strip())
            end = date.fromisoformat(parts[1].strip())
            d = start
            while d <= end:
                dates.append(d)
                d += timedelta(days=1)
        elif "," in text:
            for part in text.split(","):
                dates.append(date.fromisoformat(part.strip()))
        else:
            dates.append(date.fromisoformat(text))
    except ValueError:
        await update.message.reply_text(
            "Could not parse dates. Please use format YYYY-MM-DD.\n"
            "Examples: <code>2026-03-15</code> or <code>2026-03-15 to 2026-03-20</code>",
            parse_mode="HTML",
        )
        return ENTER_DATES

    if not dates:
        await update.message.reply_text("No valid dates found. Try again.")
        return ENTER_DATES

    context.user_data["watch_dates"] = dates

    await update.message.reply_text(
        "Enter time range to monitor (e.g. <code>18:00-21:00</code>) "
        "or send <code>any</code> for all times:",
        parse_mode="HTML",
    )
    return ENTER_TIMES


async def times_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parse time range and create the watch."""
    text = update.message.text.strip().lower()
    time_start = None
    time_end = None

    if text != "any":
        m = re.match(r"(\d{1,2}:\d{2})\s*[-\u2013]\s*(\d{1,2}:\d{2})", text)
        if not m:
            await update.message.reply_text(
                "Could not parse time. Use format <code>HH:MM-HH:MM</code> or <code>any</code>.",
                parse_mode="HTML",
            )
            return ENTER_TIMES
        time_start = time.fromisoformat(m.group(1))
        time_end = time.fromisoformat(m.group(2))

    watch = Watch(
        location_slug=context.user_data["watch_location"],
        dates=context.user_data["watch_dates"],
        time_start=time_start,
        time_end=time_end,
    )

    state_mgr = _get_state(context)
    state_mgr.add_watch(watch)

    locations = _get_locations(context)
    loc = locations.get(watch.location_slug)
    name = loc.display_name if loc else watch.location_slug

    await update.message.reply_text(
        f"\u2705 Watch created!\n\n"
        f"\U0001f4cd {name}\n"
        f"\U0001f4c5 {watch.short_description}\n"
        f"\U0001f194 <code>{watch.id}</code>",
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def watch_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Watch creation cancelled.")
    return ConversationHandler.END


def build_watch_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("watch", watch_start)],
        states={
            ENTER_POSTCODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, postcode_entered)],
            SELECT_LOCATION: [CallbackQueryHandler(location_selected, pattern=r"^loc:")],
            ENTER_DATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, dates_entered)],
            ENTER_TIMES: [MessageHandler(filters.TEXT & ~filters.COMMAND, times_entered)],
        },
        fallbacks=[CommandHandler("cancel", watch_cancel)],
    )
