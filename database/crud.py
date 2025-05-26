from typing import Any, Coroutine, Sequence

from sqlalchemy import select, update, delete, Row, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, UTC, timezone

from config.config import config
from .models import User, Cooldown, Chat


class UserCRUD:
    @staticmethod
    async def get_user(session: AsyncSession, telegram_id: int, chat_telegram_id: int) -> User | None:
        result = await session.execute(
            select(User)
            .join(Chat)
            .where(User.telegram_id == telegram_id)
            .where(Chat.chat_id == chat_telegram_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(
            session: AsyncSession,
            telegram_id: int,
            chat_telegram_id: int,
            first_name: str,
            username: str | None
    ) -> User:
        chat = await ChatCRUD.get_chat(session, chat_telegram_id)
        if chat is None:
            raise ValueError(f"Chat with telegram_id {chat_telegram_id} not found")
        is_admin = False
        if telegram_id == config.ADMIN_ID:
            is_admin = True
        user = User(
            telegram_id=telegram_id,
            chat_id=chat.id,  # внутренний ID
            first_name=first_name,
            username=username,
            registration_date=datetime.now(UTC),
            is_admin=is_admin
        )
        session.add(user)
        await session.commit()
        return user

    @staticmethod
    async def delete_user(session: AsyncSession, user: User) -> None:
        await session.execute(delete(User).where(User.id == user.id))
        await session.commit()

    @staticmethod
    async def get_chat_users(session: AsyncSession, chat_telegram_id: int) -> list[Any] | Sequence[User]:
        chat = await ChatCRUD.get_chat(session, chat_telegram_id)
        if not chat:
            return []

        result = await session.execute(
            select(User)
            .where(User.chat_id == chat.id)
            .order_by(User.pidor_count.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def update_user_and_chat(
            session: AsyncSession,
            telegram_id: int,
            chat_telegram_id: int,
            first_name: str,
            username: str | None,
            chat_title: str
    ) -> None:
        # Получаем пользователя
        result = await session.execute(
            select(User).join(Chat).where(
                User.telegram_id == telegram_id,
                Chat.chat_id == chat_telegram_id
            )
        )
        user = result.scalar_one_or_none()

        # Получаем чат
        chat = await ChatCRUD.get_chat(session, chat_telegram_id)
        if not chat:
            raise ValueError(f"Chat with telegram_id {chat_telegram_id} not found")

        # Обновляем пользователя, если найден
        if user:
            user.first_name = first_name
            user.username = username
        else:
            raise ValueError(f"User with telegram_id {telegram_id} not found in chat {chat_telegram_id}")

        # Обновляем название чата
        chat.title = chat_title

        await session.commit()


class CooldownCRUD:
    @staticmethod
    async def get_cooldown(session: AsyncSession, chat_telegram_id: int) -> Cooldown | None:
        chat = await ChatCRUD.get_chat(session, chat_telegram_id)
        if not chat:
            return None

        result = await session.execute(
            select(Cooldown).where(Cooldown.chat_id == chat.id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def check_cooldown(session: AsyncSession, chat_id: int) -> timedelta | None:
        cooldown = await CooldownCRUD.get_cooldown(session, chat_id)
        if not cooldown:
            return None

        last_activated = cooldown.last_activated
        if last_activated.tzinfo is None:
            last_activated = last_activated.replace(tzinfo=timezone.utc)

        expiration_time = last_activated + timedelta(seconds=cooldown.cooldown_seconds)
        current_time = datetime.now(timezone.utc)

        return max(expiration_time - current_time, timedelta(0)) if expiration_time > current_time else None
    @staticmethod
    async def set_cooldown(
            session: AsyncSession,
            chat_telegram_id: int,
            cooldown_seconds: int = 86400
    ) -> Cooldown:
        chat = await ChatCRUD.get_chat(session, chat_telegram_id)
        if not chat:
            raise ValueError(f"Chat with telegram_id {chat_telegram_id} not found")

        result = await session.execute(
            select(Cooldown).where(Cooldown.chat_id == chat.id)
        )
        cooldown = result.scalar_one_or_none()

        if cooldown is None:
            cooldown = Cooldown(
                chat_id=chat.id,
                cooldown_seconds=cooldown_seconds,
                last_activated=datetime.now(UTC)
            )
            session.add(cooldown)
        else:
            cooldown.last_activated = datetime.now(UTC)
            cooldown.cooldown_seconds = cooldown_seconds

        await session.commit()
        return cooldown


class ChatCRUD:
    @staticmethod
    async def get_chat(session: AsyncSession, chat_telegram_id: int) -> Chat | None:
        result = await session.execute(
            select(Chat).where(Chat.chat_id == chat_telegram_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_chat(session: AsyncSession, chat_telegram_id: int, title: str) -> Chat:
        existing = await ChatCRUD.get_chat(session, chat_telegram_id)
        if existing:
            return existing

        chat = Chat(
            chat_id=chat_telegram_id,
            title=title
        )
        session.add(chat)
        await session.commit()
        return chat
