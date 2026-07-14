"""Set up the repeating monitoring job using PTB's JobQueue."""

from __future__ import annotations

import logging
from datetime import timedelta

from telegram.ext import Application, ContextTypes

from config.settings import POLL_INTERVAL_MINUTES
from src.monitor.checker import AvailabilityChecker

logger = logging.getLogger(__name__)


async def _monitoring_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    checker: AvailabilityChecker = context.bot_data["checker"]
    try:
        await checker.check_all_links(context.bot)
    except Exception:
        logger.exception("Error in monitoring cycle")


def setup_monitoring(application: Application) -> None:
    """Register the repeating availability check job."""
    job_queue = application.job_queue
    job_queue.run_repeating(
        callback=_monitoring_callback,
        interval=timedelta(minutes=POLL_INTERVAL_MINUTES),
        first=timedelta(seconds=30),
        name="availability_monitor",
    )
    logger.info("Monitoring scheduled every %d minutes", POLL_INTERVAL_MINUTES)
