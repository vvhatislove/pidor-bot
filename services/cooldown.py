from datetime import datetime, timezone

from typing import Optional
from database.crud import CooldownCRUD
from sqlalchemy.ext.asyncio import AsyncSession
from logger import setup_logger

logger = setup_logger(__name__)


class CooldownService:
    @staticmethod
    async def check_cooldown(session: AsyncSession, chat_id: int) -> bool:
        """
        Возвращает True, если кулдаун уже сработал сегодня.
        """
        logger.debug(f"Checking date-based cooldown for chat {chat_id}")
        cooldown = await CooldownCRUD.get_cooldown(session, chat_id)
        if not cooldown:
            logger.debug(f"No cooldown set for chat {chat_id}")
            return False

        last_date = cooldown.last_activated.date()
        today_date = datetime.now(timezone.utc).date()


        if last_date == today_date:
            logger.debug(f"Cooldown already used today in chat {chat_id}")
            return True
        logger.debug(f"Cooldown not used today in chat {chat_id}")
        return False

    @staticmethod
    async def activate_cooldown(
            session: AsyncSession,
            chat_id: int,
            cooldown_seconds: int = 86400
    ) -> None:
        logger.info(f"Activating cooldown for chat_id={chat_id} with duration={cooldown_seconds} seconds")
        await CooldownCRUD.set_cooldown(session, chat_id, cooldown_seconds)
        logger.debug(f"Cooldown set for chat_id={chat_id}")
