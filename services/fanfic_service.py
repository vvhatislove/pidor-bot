import hashlib
import re
from datetime import UTC, datetime, timedelta
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FanficMessage, User
from database.repositories.fanfic_message_repository import FanficMessageRepository
from database.repositories.fanfic_usage_repository import FanficUsageRepository


FANFIC_REQUIRED_MESSAGES = 100
FANFIC_MESSAGE_LIMIT = 100
FANFIC_MAX_MESSAGE_LENGTH = 500
FANFIC_WEEKLY_LIMIT = 3
FANFIC_LIMIT_WINDOW = timedelta(days=7)


def normalize_fanfic_message(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fanfic_message_hash(text: str) -> str:
    normalized = normalize_fanfic_message(text).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def should_store_fanfic_message(text: str | None) -> bool:
    if not text:
        return False
    normalized = normalize_fanfic_message(text)
    if not normalized or normalized.startswith("/"):
        return False
    return len(normalized) >= 3


class FanficService:
    @staticmethod
    async def set_allowed(session: AsyncSession, user: User, allowed: bool) -> None:
        user.fanfic_allowed = allowed
        await session.commit()

    @staticmethod
    async def store_user_message(session: AsyncSession, user: User | None, text: str | None) -> bool:
        if not user or not user.fanfic_allowed or not should_store_fanfic_message(text):
            return False

        content = normalize_fanfic_message(text or "")
        if len(content) > FANFIC_MAX_MESSAGE_LENGTH:
            content = content[:FANFIC_MAX_MESSAGE_LENGTH].rstrip()
        content_hash = fanfic_message_hash(content)

        existing = await FanficMessageRepository.get_by_hash(session, user.id, content_hash)
        if existing:
            return False

        await FanficMessageRepository.create_message(session, user.id, content, content_hash)
        await FanficMessageRepository.trim_oldest(session, user.id, FANFIC_MESSAGE_LIMIT)
        await session.commit()
        return True

    @staticmethod
    async def count_messages(session: AsyncSession, user: User) -> int:
        return await FanficMessageRepository.count_messages(session, user.id)

    @staticmethod
    async def get_context_messages(session: AsyncSession, user: User) -> Sequence[FanficMessage]:
        return await FanficMessageRepository.get_messages(session, user.id, FANFIC_MESSAGE_LIMIT)

    @staticmethod
    def usage_window_start(now: datetime | None = None) -> datetime:
        current = now or datetime.now(UTC)
        return current - FANFIC_LIMIT_WINDOW

    @staticmethod
    async def count_recent_usages(session: AsyncSession, user: User, now: datetime | None = None) -> int:
        return await FanficUsageRepository.count_since(session, user.id, FanficService.usage_window_start(now))

    @staticmethod
    async def remaining_weekly_usages(session: AsyncSession, user: User, now: datetime | None = None) -> int:
        used = await FanficService.count_recent_usages(session, user, now)
        return max(0, FANFIC_WEEKLY_LIMIT - used)

    @staticmethod
    async def next_available_at(session: AsyncSession, user: User, now: datetime | None = None) -> datetime | None:
        since = FanficService.usage_window_start(now)
        oldest = await FanficUsageRepository.get_oldest_since(session, user.id, since)
        if not oldest:
            return None
        return oldest.created_at + FANFIC_LIMIT_WINDOW

    @staticmethod
    async def record_successful_generation(session: AsyncSession, user: User, now: datetime | None = None) -> None:
        await FanficUsageRepository.create_usage(session, user.id, now or datetime.now(UTC))
        await session.commit()
