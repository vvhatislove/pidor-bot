from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from config.config import config
from database.repositories.cooldown_repository import CooldownRepository
from database.models import User
from logger import setup_logger

logger = setup_logger(__name__)




class CooldownService:
    @staticmethod
    async def check_cooldown(session: AsyncSession, chat_id: int) -> bool:
        """
        Возвращает True, если кулдаун уже сработал сегодня (с учётом TIMEZONE).
        """
        logger.debug(f"Checking date-based cooldown for chat {chat_id}")
        cooldown = await CooldownRepository.get_cooldown(session, chat_id)
        if not cooldown:
            logger.debug(f"No cooldown set for chat {chat_id}")
            return False

        tz = ZoneInfo(config.TIMEZONE)
        now_local = datetime.now(tz)
        last_activated = cooldown.last_activated
        if last_activated.tzinfo is None:
            last_activated = last_activated.replace(tzinfo=UTC)
        last_activated_local = last_activated.astimezone(tz)

        logger.debug(f"Last activated (local): {last_activated_local.date()}, Now: {now_local.date()}")

        if last_activated_local.date() == now_local.date():
            logger.debug(f"Cooldown already used today in chat {chat_id}")
            return True
        logger.debug(f"Cooldown not used today in chat {chat_id}")
        return False

    @staticmethod
    async def activate_cooldown(
            session: AsyncSession,
            chat_id: int,
            cooldown_seconds: int = 86400,
            pidor_user_id: int | None = None,
    ) -> None:
        logger.info(f"Activating cooldown for chat_id={chat_id} with duration={cooldown_seconds} seconds")
        await CooldownRepository.set_cooldown(session, chat_id, cooldown_seconds, pidor_user_id=pidor_user_id)
        logger.debug(f"Cooldown set for chat_id={chat_id}")

    @staticmethod
    async def get_today_pidor(session: AsyncSession, chat_id: int) -> User | None:
        return await CooldownRepository.get_cooldown_pidor_user(session, chat_id)
