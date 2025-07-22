from datetime import datetime, timedelta, UTC, timezone
from typing import Any, Sequence, Optional

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.config import config
from logger import setup_logger
from .models import User, Cooldown, Chat, CurrencyTransaction, Duel, DuelStatus

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
    async def get_all_chats(session: AsyncSession) -> list[Chat]:
        result = await session.execute(select(Chat))
        chats = result.scalars().all()
        logger.info(f"Found {len(chats)} chats in total")
        return chats


class CurrencyTransactionCRUD:
    @staticmethod
    async def create_transaction(session: AsyncSession, user_id: int, amount: float,
                                 reason: str) -> CurrencyTransaction:
        if amount <= 0:
            raise ValueError(f"Невозможно создать транзакцию с amount={amount}. Значение должно быть > 0.")

        transaction = CurrencyTransaction(
            user_id=user_id,
            amount=amount,
            reason=reason,
            created_at=datetime.now(UTC)
        )
        session.add(transaction)
        return transaction

    @staticmethod
    async def get_user_transactions(session: AsyncSession, user_id: int) -> Sequence[CurrencyTransaction]:
        stmt = select(CurrencyTransaction).where(CurrencyTransaction.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_all_transactions(session: AsyncSession) -> Sequence[CurrencyTransaction]:
        stmt = select(CurrencyTransaction).order_by(CurrencyTransaction.created_at.desc())
        result = await session.execute(stmt)
        return result.scalars().all()


class DuelCRUD:

    @staticmethod
    async def create_duel(
            session: AsyncSession,
            chat_id: int,
            initiator_id: int,
            opponent_id: int,
            amount: float
    ) -> Duel:
        duel = Duel(
            chat_id=chat_id,
            initiator_id=initiator_id,
            opponent_id=opponent_id,
            amount=amount
        )
        session.add(duel)
        await session.commit()
        await session.refresh(duel)
        return duel

    @staticmethod
    async def get_duel_by_id(session: AsyncSession, duel_id: int) -> Optional[Duel]:
        result = await session.execute(
            select(Duel)
            .options(
                selectinload(Duel.initiator),
                selectinload(Duel.opponent),
                selectinload(Duel.chat),
            )
            .where(Duel.id == duel_id)
        )
        return result.scalar_one_or_none()

    # async def get_active_duels_by_chat(self, chat_id: int) -> List[Duel]:
    #     result = await self.session.execute(
    #         select(Duel).where(
    #             Duel.chat_id == chat_id,
    #             Duel.status.in_([
    #                 DuelStatus.WAITING_FOR_CONFIRMATION,
    #                 DuelStatus.WAITING_FOR_BETS,
    #                 DuelStatus.IN_PROGRESS
    #             ])
    #         )
    #     )
    #     return result.scalars().all()

    @staticmethod
    async def update_duel_status(session: AsyncSession, duel_id: int, status: DuelStatus) -> None:
        await session.execute(
            update(Duel).where(Duel.id == duel_id).values(status=status)
        )
        await session.commit()

    @staticmethod
    async def set_duel_winner(session: AsyncSession, duel_id: int, winner_id: int) -> None:
        await session.execute(
            update(Duel).where(Duel.id == duel_id).values(winner_id=winner_id)
        )
        await session.commit()

    @staticmethod
    async def get_pending_confirmation(
            session: AsyncSession,
            chat_telegram_id: int,
            opponent_telegram_id: int
    ) -> Optional[Duel]:
        result = await session.execute(
            select(Duel)
            .join(Duel.chat)
            .join(Duel.opponent)
            .where(Chat.telegram_chat_id == chat_telegram_id)
            .where(User.telegram_id == opponent_telegram_id)
            .where(Duel.status == DuelStatus.WAITING_FOR_CONFIRMATION)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_pending_or_active_duel_by_chat(
            session: AsyncSession,
            chat_telegram_id: int
    ) -> Optional[Duel]:
        result = await session.execute(
            select(Duel)
            .join(Duel.chat)
            .where(Chat.telegram_chat_id == chat_telegram_id)
            .where(Duel.status.in_([
                DuelStatus.ACTIVE,
                DuelStatus.WAITING_FOR_CONFIRMATION
            ]))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def cancel_duel_with_refund(session: AsyncSession, duel: Duel) -> None:
        if duel.status == DuelStatus.FINISHED or duel.status == DuelStatus.CANCELLED:
            return  # Нельзя отменить завершённую или уже отменённую дуэль
        current_status = duel.status
        duel.status = DuelStatus.CANCELLED

        # if current_status == DuelStatus.WAITING_FOR_CONFIRMATION:
        #     duel.initiator.balance += duel.amount
        #     await CurrencyTransactionCRUD.create_transaction(
        #         session, duel.initiator.id, duel.amount, "refund initiator bet(duel was cancelled)"
        #     )
        if current_status == DuelStatus.WAITING_FOR_CONFIRMATION:
            duel.initiator.balance += duel.amount
            duel.opponent.balance += duel.amount
            await CurrencyTransactionCRUD.create_transaction(
                session, duel.initiator.id, duel.amount, "refund initiator bet(duel was cancelled)"
            )
            await CurrencyTransactionCRUD.create_transaction(
                session, duel.opponent.id, duel.amount, "refund opponent bet(duel was cancelled)"
            )

        await session.commit()
