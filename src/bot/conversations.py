"""Multi-step conversation handler for /watch command."""

from __future__ import annotations

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

SELECT_LOCATION, ENTER_DATES, ENTER_TIMES = range(3)


def _get_locations(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Location]:
    return context.bot_data["locations"]


def _get_state(context: ContextTypes.DEFAULT_TYPE) -> StateManager:
    return context.bot_data["state"]


async def watch_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: show location selection keyboard."""
    locations = _get_locations(context)
    buttons = [
        [InlineKeyboardButton(loc.display_name, callback_data=f"loc:{slug}")]
        for slug, loc in locations.items()
    ]
    await update.message.reply_text(
        "Select a location to monitor:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return SELECT_LOCATION


async def location_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle location selection, ask for dates."""
    query = update.callback_query
    await query.answer()
    slug = query.data.replace("loc:", "")
    context.user_data["watch_location"] = slug

    locations = _get_locations(context)
    loc = locations.get(slug)
    name = loc.display_name if loc else slug

    await query.edit_message_text(
        f"📍 <b>{name}</b>\n\n"
        "Enter date(s) to monitor:\n"
        "  • Single date: <code>2026-03-15</code>\n"
        "  • Range: <code>2026-03-15 to 2026-03-20</code>\n"
        "  • Multiple: <code>2026-03-15, 2026-03-17</code>",
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
        m = re.match(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})", text)
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
        f"✅ Watch created!\n\n"
        f"📍 {name}\n"
        f"📅 {watch.short_description}\n"
        f"🆔 <code>{watch.id}</code>",
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
            SELECT_LOCATION: [CallbackQueryHandler(location_selected, pattern=r"^loc:")],
            ENTER_DATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, dates_entered)],
            ENTER_TIMES: [MessageHandler(filters.TEXT & ~filters.COMMAND, times_entered)],
        },
        fallbacks=[CommandHandler("cancel", watch_cancel)],
    )
