from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FanficUsage


class FanficUsageRepository:
    @staticmethod
    async def count_since(session: AsyncSession, user_id: int, since: datetime) -> int:
        return await session.scalar(
            select(func.count(FanficUsage.id))
            .where(FanficUsage.user_id == user_id)
            .where(FanficUsage.created_at >= since)
        ) or 0

    @staticmethod
    async def get_oldest_since(session: AsyncSession, user_id: int, since: datetime) -> FanficUsage | None:
        result = await session.execute(
            select(FanficUsage)
            .where(FanficUsage.user_id == user_id)
            .where(FanficUsage.created_at >= since)
            .order_by(FanficUsage.created_at.asc(), FanficUsage.id.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_usage(session: AsyncSession, user_id: int, created_at: datetime) -> FanficUsage:
        usage = FanficUsage(user_id=user_id, created_at=created_at)
        session.add(usage)
        await session.flush()
        return usage
