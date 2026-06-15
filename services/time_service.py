from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from config.config import config


def to_local_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(ZoneInfo(config.TIMEZONE))


def local_now() -> datetime:
    return datetime.now(ZoneInfo(config.TIMEZONE))


def format_local_datetime(value: datetime, fmt: str = "%d.%m.%Y %H:%M") -> str:
    return to_local_datetime(value).strftime(fmt)
