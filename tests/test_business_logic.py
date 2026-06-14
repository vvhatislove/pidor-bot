from database.repositories.chat_repository import ChatRepository
from database.repositories.currency_transaction_repository import CurrencyTransactionRepository
from database.repositories.duel_repository import DuelRepository
from database.repositories.user_repository import UserRepository
from database.models import DuelStatus
from database.transaction_reasons import TransactionReason, admin_add_balance_reason


async def _create_user(session, telegram_id: int, chat_id: int, first_name: str, balance: float):
    user = await UserRepository.create_user(
        session=session,
        telegram_id=telegram_id,
        chat_telegram_id=chat_id,
        first_name=first_name,
        username=f"user{telegram_id}",
    )
    user.balance = balance
    await session.commit()
    return user


async def test_increase_balance_updates_only_one_chat_user(session):
    await ChatRepository.create_chat(session, -100, "first")
    await ChatRepository.create_chat(session, -200, "second")
    first_chat_user = await _create_user(session, 42, -100, "User", 10)
    second_chat_user = await _create_user(session, 42, -200, "User", 20)

    await UserRepository.increase_balance(session, first_chat_user.id, 100)
    await session.commit()

    assert first_chat_user.balance == 110
    assert second_chat_user.balance == 20


async def test_deactivate_user_preserves_data_and_excludes_from_active_chat_users(session):
    await ChatRepository.create_chat(session, -100, "chat")
    user = await _create_user(session, 42, -100, "User", 500)
    user.pidor_count = 3
    await session.commit()

    await UserRepository.deactivate_user(session, user)

    active_users = await UserRepository.get_chat_users(session, -100)
    all_users = await UserRepository.get_chat_users(session, -100, active_only=False)

    assert active_users == []
    assert all_users == [user]
    assert user.is_active is False
    assert user.balance == 500
    assert user.pidor_count == 3

    await UserRepository.activate_user(session, user, first_name="Updated", username="updated")

    active_users = await UserRepository.get_chat_users(session, -100)

    assert active_users == [user]
    assert user.is_active is True
    assert user.first_name == "Updated"
    assert user.username == "updated"
    assert user.balance == 500
    assert user.pidor_count == 3


async def test_cancel_waiting_duel_refunds_only_initiator(session):
    chat = await ChatRepository.create_chat(session, -100, "duels")
    initiator = await _create_user(session, 1, -100, "Initiator", 900)
    opponent = await _create_user(session, 2, -100, "Opponent", 1000)
    created_duel = await DuelRepository.create_duel(session, chat.id, initiator.id, opponent.id, 100)
    duel = await DuelRepository.get_duel_by_id(session, created_duel.id)

    await DuelRepository.cancel_duel_with_refund(session, duel)

    assert duel.status == DuelStatus.CANCELLED
    assert initiator.balance == 1000
    assert opponent.balance == 1000

    transactions = await CurrencyTransactionRepository.get_all_transactions(session)
    assert len(transactions) == 1
    assert transactions[0].user_id == initiator.id
    assert transactions[0].amount == 100
    assert transactions[0].reason == TransactionReason.DUEL_INITIATOR_REFUND


async def test_transaction_stats_support_new_and_legacy_reason_values(session):
    await ChatRepository.create_chat(session, -100, "stats")
    user = await _create_user(session, 1, -100, "User", 1000)

    await CurrencyTransactionRepository.create_transaction(session, user.id, 100, TransactionReason.SLOTS_BET)
    await CurrencyTransactionRepository.create_transaction(session, user.id, 250, "slots win")
    await CurrencyTransactionRepository.create_transaction(session, user.id, 300, "duel initiator bet")
    await CurrencyTransactionRepository.create_transaction(session, user.id, 570, TransactionReason.DUEL_WINNER_PAYOUT)
    await CurrencyTransactionRepository.create_transaction(session, user.id, 50, admin_add_balance_reason(999))
    await session.commit()

    slot_bet, slot_win, slot_profit = await CurrencyTransactionRepository.get_slot_stats_for_user(session, user.id)
    duel_bet, duel_payout, duel_profit = await CurrencyTransactionRepository.get_duel_stats_for_user(session, user.id)

    assert (slot_bet, slot_win, slot_profit) == (100, 250, 150)
    assert (duel_bet, duel_payout, duel_profit) == (300, 570, 270)
