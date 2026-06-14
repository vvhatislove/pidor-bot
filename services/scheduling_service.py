import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config.config import config
from logger import setup_logger

logger = setup_logger(__name__)


async def wait_until(hour: int, minute: int):
    tz = ZoneInfo(config.TIMEZONE)
    now = datetime.now(tz)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target < now:
        target += timedelta(days=1)
    # logger.info(f"Sleeping until: {target.strftime('%Y-%m-%d %H:%M:%S')}")
    await asyncio.sleep((target - now).total_seconds())
