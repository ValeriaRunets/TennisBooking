"""Telegram bot command handlers."""

from __future__ import annotations

import functools
import logging
import re
from datetime import time

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import AUTHORIZED_CHAT_ID
from src.bot.formatters import format_link_list
from src.models.types import MonitoredLink
from src.monitor.state import StateManager

logger = logging.getLogger(__name__)

_TIME_RANGE_RE = re.compile(r"^(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})$")
_TIME_SINGLE_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def _parse_time_arg(text: str) -> tuple[time | None, time | None, str | None]:
    """Parse a time argument. Returns (time_start, time_end, error).
    'any' -> (None, None, None)
    'HH:MM-HH:MM' -> (start, end, None)
    """
    text = text.strip().lower()
    if text == "any":
        return None, None, None

    m = _TIME_RANGE_RE.match(text)
    if m:
        try:
            t_start = time.fromisoformat(m.group(1))
            t_end = time.fromisoformat(m.group(2))
            return t_start, t_end, None
        except ValueError:
            return None, None, "Invalid time values."

    return None, None, "Use format <code>HH:MM-HH:MM</code> or <code>any</code>."


def authorized_only(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if AUTHORIZED_CHAT_ID and chat_id != AUTHORIZED_CHAT_ID:
            await update.message.reply_text("Unauthorized.")
            return
        return await func(update, context)
    return wrapper


def _state(context: ContextTypes.DEFAULT_TYPE) -> StateManager:
    return context.bot_data["state"]


@authorized_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "<b>Tennis Court Monitor</b>\n\n"
        "I monitor booking pages and notify you when your desired time is free.\n\n"
        "<b>Commands:</b>\n"
        "/add &lt;url&gt; &lt;HH:MM-HH:MM|any&gt; [label]\n"
        "/remove &lt;id&gt; — Remove a link\n"
        "/list — Show monitored links\n"
        "/edit &lt;id&gt; &lt;time|url|label&gt; &lt;value&gt;\n"
        "/check &lt;id&gt; — Check a link now\n"
        "/pause — Pause monitoring\n"
        "/resume — Resume monitoring\n"
        "/status — Bot status",
        parse_mode="HTML",
    )


@authorized_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


@authorized_only
async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a new link: /add <url> <HH:MM-HH:MM|any> [label]"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /add <code>URL</code> <code>HH:MM-HH:MM</code> or <code>any</code> [label]\n\n"
            "Examples:\n"
            "<code>/add https://bookings.better.org.uk/... 18:00-21:00 Islington Tue</code>\n"
            "<code>/add https://bookings.better.org.uk/... any Saturday</code>",
            parse_mode="HTML",
        )
        return

    url = context.args[0]
    time_arg = context.args[1]

    if not url.startswith("http"):
        await update.message.reply_text("URL must start with http:// or https://")
        return

    t_start, t_end, err = _parse_time_arg(time_arg)
    if err:
        await update.message.reply_text(err, parse_mode="HTML")
        return

    label = " ".join(context.args[2:]) if len(context.args) > 2 else ""

    link = MonitoredLink(url=url, time_start=t_start, time_end=t_end, label=label)
    _state(context).add_link(link)

    await update.message.reply_text(
        f"Added!\n\n"
        f"URL: {url}\n"
        f"Time: <b>{link.time_description}</b>\n"
        f"Label: {label or '(none)'}\n"
        f"ID: <code>{link.id}</code>",
        parse_mode="HTML",
    )


@authorized_only
async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /remove <code>id</code>", parse_mode="HTML")
        return
    link_id = context.args[0]
    removed = _state(context).remove_link(link_id)
    if removed:
        await update.message.reply_text(f"Removed <code>{link_id}</code>.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"Link <code>{link_id}</code> not found.", parse_mode="HTML")


@authorized_only
async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context).load()
    await update.message.reply_text(format_link_list(state.links), parse_mode="HTML")


@authorized_only
async def cmd_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Edit a link: /edit <id> <field> <value>
    Fields: time, url, label
    """
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /edit <code>id</code> <code>time|url|label</code> <code>value</code>\n\n"
            "Examples:\n"
            "<code>/edit abc123 time 19:00-21:00</code>\n"
            "<code>/edit abc123 time any</code>\n"
            "<code>/edit abc123 label Tuesday evening</code>",
            parse_mode="HTML",
        )
        return

    link_id = context.args[0]
    field_name = context.args[1].lower()
    value = " ".join(context.args[2:])

    state_mgr = _state(context)

    if field_name == "time":
        t_start, t_end, err = _parse_time_arg(value)
        if err:
            await update.message.reply_text(err, parse_mode="HTML")
            return
        ok = state_mgr.update_link(link_id, time_start=t_start, time_end=t_end)
    elif field_name == "url":
        if not value.startswith("http"):
            await update.message.reply_text("URL must start with http:// or https://")
            return
        ok = state_mgr.update_link(link_id, url=value)
    elif field_name == "label":
        ok = state_mgr.update_link(link_id, label=value)
    else:
        await update.message.reply_text("Unknown field. Use: time, url, or label.")
        return

    if ok:
        await update.message.reply_text(f"Updated <code>{link_id}</code>: {field_name} = {value}", parse_mode="HTML")
    else:
        await update.message.reply_text(f"Link <code>{link_id}</code> not found.", parse_mode="HTML")


@authorized_only
async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """On-demand check for a specific link: /check <id>"""
    if not context.args:
        await update.message.reply_text("Usage: /check <code>id</code>", parse_mode="HTML")
        return

    link_id = context.args[0]
    state = _state(context).load()
    link = next((l for l in state.links if l.id == link_id), None)

    if not link:
        await update.message.reply_text(f"Link <code>{link_id}</code> not found.", parse_mode="HTML")
        return

    await update.message.reply_text(f"Checking {link.label or link.url}...")

    fetcher = context.bot_data["fetcher"]
    slots = await fetcher.fetch_url(link.url)

    if not slots:
        await update.message.reply_text("No slots found on the page. The page structure may have changed.")
        return

    matching = [s for s in slots if link.matches_slot(s)]

    lines = [f"<b>Results ({link.time_description}):</b>\n"]

    if matching:
        for s in matching:
            price_str = f" ({s.price})" if s.price else ""
            lines.append(
                f"  ✅ {s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')} "
                f"{s.court_name}{price_str}"
            )
        lines.append(f"\n<a href=\"{link.url}\">Book now →</a>")
    else:
        lines.append(f"  ❌ No available slots for {link.time_description}.")
        available = [s for s in slots if s.is_available]
        if available:
            lines.append(f"\nOther available times ({len(available)}):")
            for s in available[:10]:
                lines.append(f"  • {s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')} {s.court_name}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)


@authorized_only
async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state_mgr = _state(context)
    state = state_mgr.load()
    state.monitoring_enabled = False
    state_mgr.save(state)
    await update.message.reply_text("Monitoring paused. Use /resume to restart.")


@authorized_only
async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state_mgr = _state(context)
    state = state_mgr.load()
    state.monitoring_enabled = True
    state_mgr.save(state)
    await update.message.reply_text("Monitoring resumed.")


@authorized_only
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context).load()
    active_links = sum(1 for l in state.links if l.active)
    status = "active" if state.monitoring_enabled else "paused"
    await update.message.reply_text(
        f"Monitoring: {status}\n"
        f"Active links: {active_links}",
    )
