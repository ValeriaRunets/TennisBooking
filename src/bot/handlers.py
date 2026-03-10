"""Telegram bot command handlers."""

from __future__ import annotations

import functools
import logging
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import AUTHORIZED_CHAT_ID
from src.bot.formatters import format_availability, format_locations, format_watch_list
from src.models.types import Location
from src.monitor.state import StateManager

logger = logging.getLogger(__name__)


def authorized_only(func):
    """Restrict handler to the authorized user."""

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if AUTHORIZED_CHAT_ID and chat_id != AUTHORIZED_CHAT_ID:
            await update.message.reply_text("⛔ Unauthorized.")
            return
        return await func(update, context)

    return wrapper


def _state(context: ContextTypes.DEFAULT_TYPE) -> StateManager:
    return context.bot_data["state"]


def _locations(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Location]:
    return context.bot_data["locations"]


@authorized_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🎾 <b>Tennis Court Monitor</b>\n\n"
        "I'll watch for available courts on better.org.uk and notify you.\n\n"
        "<b>Commands:</b>\n"
        "/watch — Add a new court watch\n"
        "/unwatch &lt;id&gt; — Remove a watch\n"
        "/list — Show active watches\n"
        "/check &lt;location&gt; &lt;date&gt; — Check availability now\n"
        "/locations — Show available locations\n"
        "/pause — Pause monitoring\n"
        "/resume — Resume monitoring\n"
        "/status — Bot status",
        parse_mode="HTML",
    )


@authorized_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


@authorized_only
async def cmd_locations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    locations = _locations(context)
    await update.message.reply_text(format_locations(locations), parse_mode="HTML")


@authorized_only
async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context).load()
    active = [w for w in state.watches if w.active]
    locations = _locations(context)
    await update.message.reply_text(format_watch_list(active, locations), parse_mode="HTML")


@authorized_only
async def cmd_unwatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /unwatch <code>watch_id</code>", parse_mode="HTML")
        return
    watch_id = context.args[0]
    removed = _state(context).remove_watch(watch_id)
    if removed:
        await update.message.reply_text(f"✅ Watch <code>{watch_id}</code> removed.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"Watch <code>{watch_id}</code> not found.", parse_mode="HTML")


@authorized_only
async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """On-demand availability check: /check <location_slug> <date>"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /check <code>location_slug</code> <code>YYYY-MM-DD</code>\n"
            "Use /locations to see available slugs.",
            parse_mode="HTML",
        )
        return

    slug = context.args[0]
    locations = _locations(context)
    if slug not in locations:
        await update.message.reply_text(f"Unknown location: <code>{slug}</code>", parse_mode="HTML")
        return

    try:
        target_date = date.fromisoformat(context.args[1])
    except ValueError:
        await update.message.reply_text("Invalid date format. Use YYYY-MM-DD.")
        return

    location = locations[slug]
    await update.message.reply_text(f"⏳ Checking {location.display_name} for {target_date}...")

    fetcher = context.bot_data["fetcher"]
    snapshot = await fetcher.fetch(location, target_date)

    if snapshot is None:
        await update.message.reply_text("❌ Failed to fetch availability. Check logs.")
        return

    await update.message.reply_text(format_availability(snapshot, location), parse_mode="HTML")


@authorized_only
async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state_mgr = _state(context)
    state = state_mgr.load()
    state.monitoring_enabled = False
    state_mgr.save(state)
    await update.message.reply_text("⏸ Monitoring paused. Use /resume to restart.")


@authorized_only
async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state_mgr = _state(context)
    state = state_mgr.load()
    state.monitoring_enabled = True
    state_mgr.save(state)
    await update.message.reply_text("▶️ Monitoring resumed.")


@authorized_only
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context).load()
    active_watches = sum(1 for w in state.watches if w.active)
    status_emoji = "▶️" if state.monitoring_enabled else "⏸"
    await update.message.reply_text(
        f"{status_emoji} Monitoring: {'active' if state.monitoring_enabled else 'paused'}\n"
        f"📋 Active watches: {active_watches}",
    )
