from typing import Optional
from database.crud import CooldownCRUD
from sqlalchemy.ext.asyncio import AsyncSession
from logger import setup_logger

logger = setup_logger(__name__)


class CooldownService:
    @staticmethod
    async def check_cooldown(
            session: AsyncSession,
            chat_id: int
    ) -> Optional[str]:
        logger.debug(f"Checking cooldown for chat_id={chat_id}")
        remaining = await CooldownCRUD.check_cooldown(session, chat_id)

        if not remaining:
            logger.debug(f"No active cooldown for chat_id={chat_id}")
            return None

        total_hours = remaining.days * 24 + remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60

        logger.debug(f"Cooldown remaining for chat_id={chat_id}: {remaining}")

        if total_hours >= 24:
            days = total_hours // 24
            hours = total_hours % 24
            formatted = f"{days} дней {hours} часов"
            logger.debug(f"Formatted cooldown: {formatted}")
            return formatted

        if total_hours > 0:
            formatted = f"{total_hours} часов {minutes} минут"
            logger.debug(f"Formatted cooldown: {formatted}")
            return formatted

        formatted = f"{minutes} минут"
        logger.debug(f"Formatted cooldown: {formatted}")
        return formatted

    @staticmethod
    async def activate_cooldown(
            session: AsyncSession,
            chat_id: int,
            cooldown_seconds: int = 86400
    ) -> None:
        logger.info(f"Activating cooldown for chat_id={chat_id} with duration={cooldown_seconds} seconds")
        await CooldownCRUD.set_cooldown(session, chat_id, cooldown_seconds)
        logger.debug(f"Cooldown set for chat_id={chat_id}")
