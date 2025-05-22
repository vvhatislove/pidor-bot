from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, UTC
from .models import User, Cooldown


class UserCRUD:
    @staticmethod
    async def get_user(session: AsyncSession, telegram_id: int, chat_id: int) -> User | None:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
            .where(User.chat_id == chat_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(
        session: AsyncSession,
        telegram_id: int,
        chat_id: int,
        first_name: str,
        username: str | None
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            chat_id=chat_id,
            first_name=first_name,
            username=username,
            registration_date=datetime.utcnow()
        )
        session.add(user)
        await session.commit()
        return user

    @staticmethod
    async def delete_user(session: AsyncSession, user: User) -> None:
        await session.execute(
            delete(User)
            .where(User.id == user.id)
        )
        await session.commit()

    @staticmethod
    async def get_chat_users(session: AsyncSession, chat_id: int) -> list[User]:
        result = await session.execute(
            select(User)
            .where(User.chat_id == chat_id)
            .order_by(User.pidor_count.desc())
        )
        return list(result.scalars().all())


class CooldownCRUD:
    @staticmethod
    async def get_cooldown(session: AsyncSession, chat_id: int) -> Cooldown | None:
        result = await session.execute(
            select(Cooldown)
            .where(Cooldown.chat_id == chat_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def check_cooldown(session: AsyncSession, chat_id: int) -> timedelta | None:
        cooldown = await CooldownCRUD.get_cooldown(session, chat_id)
        if not cooldown:
            return None

        current_time = datetime.now(UTC)
        expiration_time = cooldown.last_activated + timedelta(seconds=cooldown.cooldown_seconds)

        # Убедимся, что оба значения времени имеют UTC
        if cooldown.last_activated.tzinfo is None:
            expiration_time = expiration_time.replace(tzinfo=UTC)

        remaining = expiration_time - current_time
        return remaining if remaining.total_seconds() > 0 else None

    @staticmethod
    async def set_cooldown(
            session: AsyncSession,
            chat_id: int,
            cooldown_seconds: int = 86400
    ) -> Cooldown:
        cooldown = await CooldownCRUD.get_cooldown(session, chat_id)

        if not cooldown:
            cooldown = Cooldown(
                chat_id=chat_id,
                cooldown_seconds=cooldown_seconds,
                last_activated=datetime.now(UTC)
            )
            session.add(cooldown)
        else:
            cooldown.last_activated = datetime.now(UTC)
            cooldown.cooldown_seconds = cooldown_seconds

        await session.commit()
        return cooldown
