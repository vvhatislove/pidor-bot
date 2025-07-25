from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Chat
from logger import setup_logger

logger = setup_logger(__name__)

class ChatCRUD:
    @staticmethod
    async def get_chat(session: AsyncSession, telegram_chat_id: int) -> Chat | None:
        logger.debug(f"Looking up chat {telegram_chat_id}")
        result = await session.execute(
            select(Chat).where(Chat.telegram_chat_id == telegram_chat_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_chat(session: AsyncSession, chat_telegram_id: int, title: str) -> Chat:
        logger.info(f"Creating chat {chat_telegram_id} ({title})")
        existing = await ChatCRUD.get_chat(session, chat_telegram_id)
        if existing:
            logger.debug(f"Chat {chat_telegram_id} already exists")
            return existing

        chat = Chat(
            telegram_chat_id=chat_telegram_id,
            title=title
        )
        session.add(chat)
        await session.commit()
        logger.info(f"Successfully created chat {chat_telegram_id}")
        return chat

    @staticmethod
    async def get_all_chats(session: AsyncSession) -> Sequence[Chat]:
        result = await session.execute(select(Chat))
        chats = result.scalars().all()
        logger.info(f"Found {len(chats)} chats in total")
        return chats

    @staticmethod
    async def get_auto_pidor_chats(session: AsyncSession) -> list[Chat]:
        result = await session.execute(select(Chat))
        all_chats = result.scalars().all()
        return [c for c in all_chats if c.auto_pidor is True]
