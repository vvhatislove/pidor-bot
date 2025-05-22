from datetime import timedelta
from typing import Optional
from database.crud import CooldownCRUD
from sqlalchemy.ext.asyncio import AsyncSession


class CooldownService:
    @staticmethod
    async def check_cooldown(
            session: AsyncSession,
            chat_id: int
    ) -> Optional[str]:
        remaining = await CooldownCRUD.check_cooldown(session, chat_id)
        if not remaining:
            return None

        total_hours = remaining.days * 24 + remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60

        if total_hours >= 24:
            days = total_hours // 24
            hours = total_hours % 24
            return f"{days} дней {hours} часов"

        if total_hours > 0:
            return f"{total_hours} часов {minutes} минут"
        return f"{minutes} минут"

    @staticmethod
    async def activate_cooldown(
            session: AsyncSession,
            chat_id: int,
            cooldown_seconds: int = 86400
    ) -> None:
        await CooldownCRUD.set_cooldown(session, chat_id, cooldown_seconds)