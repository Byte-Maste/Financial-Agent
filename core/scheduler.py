import asyncio
import time

from core.config import settings
from core.logger import logger
from services.monitoring_service import run_monitoring_sweep


_sweep_task: asyncio.Task | None = None


async def _sweep_loop() -> None:
    interval_seconds = settings.monitoring_interval_hours * 3600
    logger.info(
        f"Scheduler initialized | interval={settings.monitoring_interval_hours}h "
        f"({interval_seconds}s)"
    )
    while True:
        try:
            await run_monitoring_sweep()
        except Exception as e:
            logger.error(f"Sweep task crashed: {e}")
        await asyncio.sleep(interval_seconds)


def start_scheduler() -> None:
    global _sweep_task
    if _sweep_task is None or _sweep_task.done():
        _sweep_task = asyncio.create_task(_sweep_loop())
        logger.info("Scheduler background task started")


def stop_scheduler() -> None:
    global _sweep_task
    if _sweep_task and not _sweep_task.done():
        _sweep_task.cancel()
        logger.info("Scheduler background task cancelled")
