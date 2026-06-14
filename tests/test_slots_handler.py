from types import SimpleNamespace

import pytest

from database.repositories.chat_repository import ChatRepository
from database.repositories.currency_transaction_repository import CurrencyTransactionRepository
from database.repositories.user_repository import UserRepository
from database.transaction_reasons import TransactionReason
from handlers.user.slots import cmd_slots


class FakeMessage:
    def __init__(self, text: str, dice_value: int | None = None, dice_error: Exception | None = None):
        self.text = text
        self.chat = SimpleNamespace(id=-100, type="group", title="chat")
        self.from_user = SimpleNamespace(id=1)
        self.dice_value = dice_value
        self.dice_error = dice_error
        self.answers = []
        self.replies = []

    async def answer(self, text: str, **kwargs):
        self.answers.append(text)

    async def reply(self, text: str, **kwargs):
        self.replies.append(text)

    async def answer_dice(self, **kwargs):
        if self.dice_error:
            raise self.dice_error
        return SimpleNamespace(dice=SimpleNamespace(value=self.dice_value))


async def _create_registered_user(session, balance: float):
    await ChatRepository.create_chat(session, -100, "chat")
    user = await UserRepository.create_user(
        session=session,
        telegram_id=1,
        chat_telegram_id=-100,
        first_name="User",
        username="user",
    )
    user.balance = balance
    await session.commit()
    return user


async def test_slots_handler_accepts_bot_mention_and_applies_payout(monkeypatch, session):
    user = await _create_registered_user(session, 200)
    message = FakeMessage("/slots@TestBot 100", dice_value=1)

    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr("handlers.user.slots.asyncio.sleep", fake_sleep)

    await cmd_slots(message, session)

    assert user.balance == 688

    transactions = await CurrencyTransactionRepository.get_user_transactions(session, user.id)
    assert [tx.reason for tx in transactions] == [TransactionReason.SLOTS_BET, TransactionReason.SLOTS_WIN]
    assert [tx.amount for tx in transactions] == [100, 588]
    assert "Выигрыш: 600.00" in message.answers[-1]


async def test_slots_handler_does_not_charge_if_dice_send_fails(session):
    user = await _create_registered_user(session, 200)
    message = FakeMessage("/slots 100", dice_error=RuntimeError("telegram failed"))

    with pytest.raises(RuntimeError):
        await cmd_slots(message, session)

    assert user.balance == 200
    assert await CurrencyTransactionRepository.get_user_transactions(session, user.id) == []


async def test_slots_allin_allows_positive_balance_below_min_regular_bet(monkeypatch, session):
    user = await _create_registered_user(session, 0.50)
    message = FakeMessage("/slots allin", dice_value=7)

    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr("handlers.user.slots.asyncio.sleep", fake_sleep)

    await cmd_slots(message, session)

    assert user.balance == 0
    transactions = await CurrencyTransactionRepository.get_user_transactions(session, user.id)
    assert len(transactions) == 1
    assert transactions[0].amount == 0.50
    assert not any("недостаточно" in answer.lower() for answer in message.answers)
