from datetime import timedelta, timezone, datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.CRUD.chat_crud import ChatCRUD
from database.models import Cooldown
from logger import setup_logger

logger = setup_logger(__name__)

class CooldownCRUD:
    @staticmethod
    async def get_cooldown(session: AsyncSession, chat_telegram_id: int) -> Cooldown | None:
        logger.debug(f"Getting cooldown for chat {chat_telegram_id}")
        chat = await ChatCRUD.get_chat(session, chat_telegram_id)
        if not chat:
            logger.warning(f"Chat {chat_telegram_id} not found when getting cooldown")
            return None

        result = await session.execute(
            select(Cooldown).where(Cooldown.chat_id == chat.id)
        )
        cooldown = result.scalar_one_or_none()
        if cooldown:
            logger.debug(f"Found cooldown for chat {chat_telegram_id}")
        else:
            logger.debug(f"No cooldown found for chat {chat_telegram_id}")
        return cooldown

    @staticmethod
    async def check_cooldown(session: AsyncSession, chat_id: int) -> timedelta | None:
        logger.debug(f"Checking cooldown status for chat {chat_id}")
        cooldown = await CooldownCRUD.get_cooldown(session, chat_id)
        if not cooldown:
            logger.debug(f"No cooldown set for chat {chat_id}")
            return None

        last_activated = cooldown.last_activated
        if last_activated.tzinfo is None:
            last_activated = last_activated.replace(tzinfo=timezone.utc)

        expiration_time = last_activated + timedelta(seconds=cooldown.cooldown_seconds)
        current_time = datetime.now(timezone.utc)

        remaining = max(expiration_time - current_time, timedelta(0)) if expiration_time > current_time else None
        if remaining:
            logger.debug(f"Cooldown active for chat {chat_id}, {remaining} remaining")
        else:
            logger.debug(f"Cooldown expired for chat {chat_id}")
        return remaining

    @staticmethod
    async def set_cooldown(
            session: AsyncSession,
            chat_telegram_id: int,
            cooldown_seconds: int = 86400
    ) -> Cooldown:
        logger.info(f"Setting cooldown for chat {chat_telegram_id} to {cooldown_seconds} seconds")
        chat = await ChatCRUD.get_chat(session, chat_telegram_id)
        if not chat:
            logger.error(f"Chat {chat_telegram_id} not found when setting cooldown")
            raise ValueError(f"Chat with telegram_id {chat_telegram_id} not found")

        result = await session.execute(
            select(Cooldown).where(Cooldown.chat_id == chat.id)
        )
        cooldown = result.scalar_one_or_none()

        if cooldown is None:
            logger.debug(f"Creating new cooldown for chat {chat_telegram_id}")
            cooldown = Cooldown(
                chat_id=chat.id,
                cooldown_seconds=cooldown_seconds,
                last_activated=datetime.now(UTC)
            )
            session.add(cooldown)
        else:
            logger.debug(f"Updating existing cooldown for chat {chat_telegram_id}")
            cooldown.last_activated = datetime.now(UTC)
            cooldown.cooldown_seconds = cooldown_seconds

        await session.commit()
        logger.info(f"Cooldown set successfully for chat {chat_telegram_id}")
        return cooldown
