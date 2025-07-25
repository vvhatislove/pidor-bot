from datetime import datetime, UTC
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CurrencyTransaction
from logger import setup_logger

logger = setup_logger(__name__)

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

    @staticmethod
    async def get_currency_stats(session: AsyncSession, user_id: int) -> tuple[float, int]:
        result = await session.execute(
            select(CurrencyTransaction).where(CurrencyTransaction.user_id == user_id)
        )
        transactions = result.scalars().all()
        total_amount = sum(t.amount for t in transactions)
        return total_amount, len(transactions)

    @staticmethod
    async def get_duel_stats_for_user(session: AsyncSession, user_id: int) -> tuple[float, float, float]:
        result = await session.execute(
            select(CurrencyTransaction).where(CurrencyTransaction.user_id == user_id)
        )
        transactions = result.scalars().all()

        total_bet = 0.0
        total_payout = 0.0

        for tx in transactions:
            reason = tx.reason.lower()
            if "duel" in reason:
                if "bet" in reason:
                    total_bet += tx.amount
                elif "payout" in reason:
                    total_payout += tx.amount

        profit = total_payout - total_bet
        return total_bet, total_payout, profit

    @staticmethod
    async def get_slot_stats_for_user(session: AsyncSession, user_id: int) -> tuple[float, float, float]:
        result = await session.execute(
            select(CurrencyTransaction).where(CurrencyTransaction.user_id == user_id)
        )
        transactions = result.scalars().all()

        total_bet = 0.0
        total_win = 0.0

        for tx in transactions:
            reason = tx.reason.lower()
            if "slots" in reason:
                if "bet" in reason:
                    total_bet += tx.amount
                elif "win" in reason:
                    total_win += tx.amount

        profit = total_win - total_bet
        return total_bet, total_win, profit
