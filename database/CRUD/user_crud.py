from datetime import datetime, UTC
from typing import Any, Sequence

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import config
from database.CRUD.chat_crud import ChatCRUD
from database.models import User, Chat
from logger import setup_logger

logger = setup_logger(__name__)


class UserCRUD:
    @staticmethod
    async def get_user_by_username(session: AsyncSession, username: str, chat_telegram_id: int) -> User | None:
        result = await session.execute(
            select(User)
            .join(Chat)
            .where(User.username == username.lstrip("@"))
            .where(Chat.telegram_chat_id == chat_telegram_id)
        )
        user = result.scalar_one_or_none()
        return user

    @staticmethod
    async def increase_balance(session: AsyncSession, telegram_id: int, amount: int):
        stmt = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(balance=User.balance + amount)
            .execution_options(synchronize_session="fetch")
        )
        await session.execute(stmt)
        await session.commit()

    @staticmethod
    async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int, chat_telegram_id: int) -> User | None:
        logger.debug(f"Attempting to get user {telegram_id} from chat {chat_telegram_id}")
        result = await session.execute(
            select(User)
            .join(Chat)
            .where(User.telegram_id == telegram_id)
            .where(Chat.telegram_chat_id == chat_telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            logger.debug(f"Found user {telegram_id} in chat {chat_telegram_id}")
        else:
            logger.debug(f"User {telegram_id} not found in chat {chat_telegram_id}")
        return user

    @staticmethod
    async def create_user(
            session: AsyncSession,
            telegram_id: int,
            chat_telegram_id: int,
            first_name: str,
            username: str | None
    ) -> User:
        logger.info(f"Creating user {telegram_id} ({first_name}) in chat {chat_telegram_id}")
        chat = await ChatCRUD.get_chat(session, chat_telegram_id)
        if chat is None:
            logger.error(f"Chat {chat_telegram_id} not found when creating user {telegram_id}")
            raise ValueError(f"Chat with telegram_id {chat_telegram_id} not found")

        is_admin = telegram_id == config.ADMIN_ID
        if is_admin:
            logger.debug(f"User {telegram_id} identified as admin")

        user = User(
            telegram_id=telegram_id,
            chat_id=chat.id,
            first_name=first_name,
            username=username,
            registration_date=datetime.now(UTC),
            is_admin=is_admin
        )
        session.add(user)
        await session.commit()
        logger.info(f"Successfully created user {telegram_id} in chat {chat_telegram_id}")
        return user

    @staticmethod
    async def delete_user(session: AsyncSession, user: User) -> None:
        logger.info(f"Deleting user {user.telegram_id} from chat {user.chat_id}")
        await session.execute(delete(User).where(User.id == user.id))
        await session.commit()
        logger.info(f"Successfully deleted user {user.telegram_id}")

    @staticmethod
    async def get_chat_users(session: AsyncSession, chat_telegram_id: int) -> list[Any] | Sequence[User]:
        logger.debug(f"Getting all users for chat {chat_telegram_id}")
        chat = await ChatCRUD.get_chat(session, chat_telegram_id)
        if not chat:
            logger.warning(f"Chat {chat_telegram_id} not found when getting users")
            return []

        result = await session.execute(
            select(User)
            .where(User.chat_id == chat.id)
            .order_by(User.pidor_count.desc())
        )
        users = result.scalars().all()
        logger.debug(f"Found {len(users)} users in chat {chat_telegram_id}")
        return users

    @staticmethod
    async def update_user_and_chat(
            session: AsyncSession,
            telegram_id: int,
            chat_telegram_id: int,
            first_name: str,
            username: str | None,
            chat_title: str
    ) -> None:
        logger.info(f"Updating user {telegram_id} and chat {chat_telegram_id}")

        result = await session.execute(
            select(User).join(Chat).where(
                User.telegram_id == telegram_id,
                Chat.telegram_chat_id == chat_telegram_id
            )
        )
        user = result.scalar_one_or_none()

        chat = await ChatCRUD.get_chat(session, chat_telegram_id)
        if not chat:
            logger.error(f"Chat {chat_telegram_id} not found during update")
            raise ValueError(f"Chat with telegram_id {chat_telegram_id} not found")

        if user:
            logger.debug(f"Updating user {telegram_id} details")
            user.first_name = first_name
            user.username = username
        else:
            logger.error(f"User {telegram_id} not found in chat {chat_telegram_id}")
            raise ValueError(f"User with telegram_id {telegram_id} not found in chat {chat_telegram_id}")

        logger.debug(f"Updating chat {chat_telegram_id} title to '{chat_title}'")
        chat.title = chat_title

        await session.commit()
        logger.info("Update completed successfully")
