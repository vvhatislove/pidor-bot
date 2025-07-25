from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.CRUD.currency_transaction_crud import CurrencyTransactionCRUD
from database.models import Duel, DuelStatus, Chat, User
from logger import setup_logger

logger = setup_logger(__name__)

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

    @staticmethod
    async def count_duel_wins(session: AsyncSession, user_id: int) -> int:
        result = await session.execute(
            select(Duel).where(Duel.winner_id == user_id)
        )
        return len(result.scalars().all())
