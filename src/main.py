"""Entry point: wires together bot, scraper, scheduler, and state."""

from __future__ import annotations

import json
import logging
import sys

from telegram.ext import ApplicationBuilder, CommandHandler

from config.settings import (
    AUTHORIZED_CHAT_ID,
    LOCATIONS_FILE,
    LOG_LEVEL,
    TELEGRAM_BOT_TOKEN,
)
from src.bot.conversations import build_watch_conversation
from src.bot.handlers import (
    cmd_calibrate,
    cmd_check,
    cmd_help,
    cmd_list,
    cmd_locations,
    cmd_pause,
    cmd_refresh,
    cmd_resume,
    cmd_start,
    cmd_status,
    cmd_unwatch,
)
from src.models.types import Location
from src.monitor.checker import AvailabilityChecker
from src.monitor.scheduler import setup_monitoring
from src.monitor.state import StateManager
from src.scraper.availability import AvailabilityFetcher
from src.scraper.browser import BrowserManager
from src.scraper.locations import load_venue_cache


def _load_locations() -> dict[str, Location]:
    """Load locations from venue cache, falling back to static config."""
    cached = load_venue_cache()
    if cached:
        return {
            item["slug"]: Location(
                slug=item["slug"],
                display_name=item["display_name"],
                activity_slug=item["activity_slug"],
                postcode=item.get("postcode"),
                lat=item.get("lat"),
                lon=item.get("lon"),
            )
            for item in cached
        }

    # Fallback to static locations.json
    raw = json.loads(LOCATIONS_FILE.read_text(encoding="utf-8"))
    return {
        item["slug"]: Location(
            slug=item["slug"],
            display_name=item["display_name"],
            activity_slug=item["activity_slug"],
        )
        for item in raw
    }


def _setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        stream=sys.stdout,
    )


async def _on_shutdown(application) -> None:
    browser: BrowserManager = application.bot_data.get("browser")
    if browser:
        await browser.stop()


def main() -> None:
    _setup_logging()
    logger = logging.getLogger(__name__)

    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set. Copy .env.example to .env and fill in values.")
        sys.exit(1)

    if not AUTHORIZED_CHAT_ID:
        logger.warning("AUTHORIZED_CHAT_ID not set — bot will accept commands from anyone!")

    # Load locations
    locations = _load_locations()
    logger.info("Loaded %d locations", len(locations))

    # Initialize components
    browser = BrowserManager()
    state = StateManager()
    fetcher = AvailabilityFetcher(browser)
    checker = AvailabilityChecker(fetcher, state, locations, AUTHORIZED_CHAT_ID)

    # Build Telegram application
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.bot_data["browser"] = browser
    app.bot_data["state"] = state
    app.bot_data["fetcher"] = fetcher
    app.bot_data["checker"] = checker
    app.bot_data["locations"] = locations

    # Register handlers
    app.add_handler(build_watch_conversation())
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("locations", cmd_locations))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("unwatch", cmd_unwatch))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("calibrate", cmd_calibrate))
    app.add_handler(CommandHandler("refresh", cmd_refresh))

    # Setup monitoring scheduler
    setup_monitoring(app)

    # Register post_init to start browser when the app starts
    async def post_init(application) -> None:
        browser_mgr: BrowserManager = application.bot_data["browser"]
        await browser_mgr.start(headless=True)
        logger.info("Browser started")

    async def post_shutdown(application) -> None:
        browser_mgr: BrowserManager = application.bot_data["browser"]
        await browser_mgr.stop()

    app.post_init = post_init
    app.post_shutdown = post_shutdown

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
