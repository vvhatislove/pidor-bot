from typing import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FanficMessage


class FanficMessageRepository:
    @staticmethod
    async def get_by_hash(session: AsyncSession, user_id: int, content_hash: str) -> FanficMessage | None:
        result = await session.execute(
            select(FanficMessage)
            .where(FanficMessage.user_id == user_id)
            .where(FanficMessage.content_hash == content_hash)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_message(session: AsyncSession, user_id: int, content: str, content_hash: str) -> FanficMessage:
        message = FanficMessage(user_id=user_id, content=content, content_hash=content_hash)
        session.add(message)
        await session.flush()
        return message

    @staticmethod
    async def count_messages(session: AsyncSession, user_id: int) -> int:
        return await session.scalar(
            select(func.count(FanficMessage.id)).where(FanficMessage.user_id == user_id)
        ) or 0

    @staticmethod
    async def get_messages(session: AsyncSession, user_id: int, limit: int | None = None) -> Sequence[FanficMessage]:
        stmt = (
            select(FanficMessage)
            .where(FanficMessage.user_id == user_id)
            .order_by(FanficMessage.created_at.asc(), FanficMessage.id.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def trim_oldest(session: AsyncSession, user_id: int, keep_limit: int) -> int:
        excess = await FanficMessageRepository.count_messages(session, user_id) - keep_limit
        if excess <= 0:
            return 0

        oldest_ids = await session.scalars(
            select(FanficMessage.id)
            .where(FanficMessage.user_id == user_id)
            .order_by(FanficMessage.created_at.asc(), FanficMessage.id.asc())
            .limit(excess)
        )
        ids_to_delete = list(oldest_ids)
        if not ids_to_delete:
            return 0

        await session.execute(delete(FanficMessage).where(FanficMessage.id.in_(ids_to_delete)))
        return len(ids_to_delete)
