from datetime import datetime, UTC
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.money_format import money_2
from database.models import CurrencyTransaction
from database.transaction_reasons import TransactionReason, normalize_transaction_reason, transaction_display_name
from logger import setup_logger

logger = setup_logger(__name__)

class CurrencyTransactionRepository:
    @staticmethod
    async def create_transaction(session: AsyncSession, user_id: int, amount: float,
                                 reason: str) -> CurrencyTransaction:
        amount = money_2(amount)
        if amount <= 0:
            raise ValueError(f"Невозможно создать транзакцию с amount={amount}. Значение должно быть > 0.")
        reason = reason.strip()
        if not reason:
            raise ValueError("Невозможно создать транзакцию без reason.")

        transaction = CurrencyTransaction(
            user_id=user_id,
            amount=amount,
            reason=reason,
            created_at=datetime.now(UTC)
        )
        session.add(transaction)
        logger.info(
            "currency transaction: user_id=%s amount=%.2f reason=%s display=%s",
            user_id,
            amount,
            reason,
            transaction_display_name(reason),
        )
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
            reason = normalize_transaction_reason(tx.reason)
            if reason in {TransactionReason.DUEL_INITIATOR_BET, TransactionReason.DUEL_OPPONENT_BET}:
                total_bet += tx.amount
            elif reason == TransactionReason.DUEL_WINNER_PAYOUT:
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
            reason = normalize_transaction_reason(tx.reason)
            if reason == TransactionReason.SLOTS_BET:
                total_bet += tx.amount
            elif reason == TransactionReason.SLOTS_WIN:
                total_win += tx.amount

        profit = total_win - total_bet
        return total_bet, total_win, profit
