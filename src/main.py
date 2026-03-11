"""Entry point: wires together bot, scraper, scheduler, and state."""

from __future__ import annotations

import logging
import sys

from telegram.ext import ApplicationBuilder, CommandHandler

from config.settings import (
    AUTHORIZED_CHAT_ID,
    LOG_LEVEL,
    TELEGRAM_BOT_TOKEN,
)
from src.bot.handlers import (
    cmd_add,
    cmd_check,
    cmd_edit,
    cmd_help,
    cmd_list,
    cmd_pause,
    cmd_remove,
    cmd_resume,
    cmd_start,
    cmd_status,
)
from src.monitor.checker import AvailabilityChecker
from src.monitor.scheduler import setup_monitoring
from src.monitor.state import StateManager
from src.scraper.availability import AvailabilityFetcher
from src.scraper.browser import BrowserManager


def _setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        stream=sys.stdout,
    )


def main() -> None:
    _setup_logging()
    logger = logging.getLogger(__name__)

    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set. Copy .env.example to .env and fill in values.")
        sys.exit(1)

    if not AUTHORIZED_CHAT_ID:
        logger.warning("AUTHORIZED_CHAT_ID not set — bot will accept commands from anyone!")

    # Initialize components
    browser = BrowserManager()
    state = StateManager()
    fetcher = AvailabilityFetcher(browser)
    checker = AvailabilityChecker(fetcher, state, AUTHORIZED_CHAT_ID)

    # Build Telegram application
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.bot_data["browser"] = browser
    app.bot_data["state"] = state
    app.bot_data["fetcher"] = fetcher
    app.bot_data["checker"] = checker

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("edit", cmd_edit))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CommandHandler("status", cmd_status))

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
