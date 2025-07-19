import asyncio
from random import choice
import re
from datetime import datetime, UTC, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import AIPromt, CommandText
from database.crud import UserCRUD, DuelCRUD, ChatCRUD, CurrencyTransactionCRUD
from database.models import DuelStatus
from logger import setup_logger
from services.ai_service import AIService
from services.duel_logic import wait_for_acceptance

router = Router()
logger = setup_logger(__name__)

@router.message(Command("duel"))
async def cmd_duel(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return

    pattern = r"/duel\s+@(\w+)\s+(\d+(?:[.,]\d{1,2})?)"
    match = re.match(pattern, message.text.strip())
    if not match:
        await message.answer("❌ Неверный формат.\nИспользуй: <code>/duel @username 100</code>", parse_mode="HTML")
        return

    username_opponent, amount_str = match.groups()
    amount = float(amount_str.replace(",", "."))

    if not (0 < amount <= 1000):
        await message.answer("💰 Сумма должна быть от 1 до 1000 PidorCoins.")
        return

    if username_opponent == message.from_user.username:
        await message.answer("🤡 Нельзя драться самому с собой, шизик.")
        return
    
    initiator = await UserCRUD.get_user_by_username(session, message.from_user.username, message.chat.id)
    if not initiator:
        await message.answer("🚫 Вы не зарегистрированы в чате.")
        return

    opponent = await UserCRUD.get_user_by_username(session, username_opponent, message.chat.id)
    if not opponent:
        await message.answer(f"👤 Пользователь @{username_opponent} не зарегистрирован.")
        return
    print(initiator.balance)
    if initiator.balance < amount:
        await message.answer("❌ У вас недостаточно PidorCoins.")
        return

    if opponent.balance < amount:
        await message.answer(f"❌ У пользователя @{username_opponent} недостаточно средств.")
        return

    duel = await DuelCRUD.get_pending_or_active_duel_by_chat(session, message.chat.id)
    if duel:
        created_at = duel.created_at.replace(tzinfo=UTC) if duel.created_at.tzinfo is None else duel.created_at
        if datetime.now(UTC) - created_at > timedelta(minutes=10):
            await DuelCRUD.cancel_duel_with_refund(session, duel)
            logger.info(f"Cancelled duel {duel.id} in chat {duel.chat_id} due to timeout")
        else:
            await message.answer("⚔️ Уже идёт дуэль или кто-то вызван. Подожди завершения.")
            return

    chat = await ChatCRUD.get_chat(session, message.chat.id)
    initiator.balance -= amount
    duel = await DuelCRUD.create_duel(session, chat.id, initiator.id, opponent.id, amount)
    await CurrencyTransactionCRUD.create_transaction(session, initiator.id, amount, "duel initiator bet")
    await session.commit()

    await message.answer(
        f"⚔️ @{message.from_user.username} по-пидорски вызвал @{username_opponent} на дуэль на сумму {amount} 🪙 PidorCoins!\n\n/accept_duel - принять дуэль\n/cancel_duel - отклонить дуэль"
    )
    asyncio.create_task(wait_for_acceptance(message.bot, session, duel.id, message.chat.id))


@router.message(Command("accept_duel"))
async def cmd_accept_duel(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return

    duel = await DuelCRUD.get_pending_confirmation(session, message.chat.id, message.from_user.id)
    if not duel:
        await message.answer("❗️ У тебя нет активных дуэлей.")
        return

    if duel.opponent.balance < duel.amount:
        duel.status = DuelStatus.CANCELLED
        await session.commit()
        await message.answer("💸 У вас недостаточно монет для принятия дуэли. Дуэль отменена.")
        return

    # Снимаем ставку с оппонента
    duel.opponent.balance -= duel.amount
    duel.status = DuelStatus.FINISHED
    duel.accepted_at = datetime.now(UTC)

    # Выбираем победителя
    initiator = duel.initiator
    opponent = duel.opponent
    winner = choice([initiator, opponent])
    duel.winner_id = winner.id

    # Выплата: сумма двух ставок минус комиссия
    commission = 0.05
    payout = round(duel.amount * 2 * (1 - commission), 2)
    winner.balance += payout

    # Записываем транзакции
    await CurrencyTransactionCRUD.create_transaction(session, duel.opponent.id, duel.amount, "duel opponent bet")
    await CurrencyTransactionCRUD.create_transaction(session, winner.id, payout, "duel winner payout")
    await session.commit()

    # Сообщение в чат
    winner_name = winner.username
    loser_name = initiator.username if winner == opponent else opponent.username
    
    await message.bot.send_message(message.chat.id,"🔍Поиск победителя...")
    duel_fight_message = await AIService.get_response("", AIPromt.DUEL_WINNER_CHOICE_PROMT)
    await asyncio.sleep(2)  # Имитация задержки для эффекта
    await message.bot.send_message(message.chat.id, duel_fight_message.format(winner=winner_name, loser=loser_name))
    await message.answer(
        f"⚔️ Дуэль завершена!\n"
        f"🏆 Победил: <b>@{winner_name}</b>\n"
        f"☠️ Проиграл: @{loser_name}\n"
        f"💰 Выплата: {payout} PidorCoins (комиссия {int(commission*100)}%)",
        parse_mode="HTML"
    )
    
@router.message(Command("cancel_duel"))
async def cmd_cancel_duel(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return

    duel = await DuelCRUD.get_pending_confirmation(session, message.chat.id, message.from_user.id)
    if not duel:
        await message.answer("❗️ У тебя нет активных дуэлей, которые можно отменить.")
        return

    await DuelCRUD.cancel_duel_with_refund(session, duel)
    await session.commit()

    opponent_username = duel.opponent.username if duel.opponent else "неизвестный"
    await message.answer(
        f"❌ Дуэль с @{opponent_username} отменена.\n🪙 Ставка возвращена на баланс."
    )
