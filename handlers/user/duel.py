import asyncio
import re
from datetime import datetime, timedelta, UTC
from random import choice

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import AIPromt, CommandText
from database.CRUD.duel_crud import DuelCRUD
from database.CRUD.currency_transaction_crud import CurrencyTransactionCRUD
from database.CRUD.chat_crud import ChatCRUD
from database.CRUD.user_crud import UserCRUD
from database.money_format import money_2
from database.models import DuelStatus
from handlers.utils.utils import get_display_name
from logger import setup_logger
from handlers.utils.AI import AI
from services.duel_service import wait_for_acceptance

router = Router()
logger = setup_logger(__name__)


@router.message(Command("duel"))
async def cmd_duel(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return
    initiator = await UserCRUD.get_user_by_telegram_id(session, message.from_user.id, message.chat.id)
    if not initiator:
        await message.answer("🚫 Вы не зарегистрированы в чате.")
        return
    reply = message.reply_to_message

    #Парсинг аргументов
    pattern_named = r"/duel\s+@(\w+)\s+(\d+(?:[.,]\d{1,2})?)"
    pattern_reply = r"/duel\s+(\d+(?:[.,]\d{1,2})?)"

    if re.match(pattern_named, message.text.strip()):
        match = re.match(pattern_named, message.text.strip())
        username_opponent, bet_str = match.groups()
        opponent_user = await UserCRUD.get_user_by_username(session, username_opponent, message.chat.id)
        if not opponent_user:
            await message.answer(f"👤 Пользователь @{username_opponent} не зарегистрирован. Или у этого \"особенного\" нет юзернейма в тг.\n\n"
                                 f"Попробуй вызвать его в ответ на сообщение <code>/duel *ставка*</code>", parse_mode="HTML")
            return
        opponent_display = get_display_name(opponent_user)

    elif reply and re.match(pattern_reply, message.text.strip()):
        match = re.match(pattern_reply, message.text.strip())
        bet_str = match.group(1)
        opponent_user = await UserCRUD.get_user_by_telegram_id(session, reply.from_user.id, message.chat.id)
        if not opponent_user:
            await message.answer("👤 Пользователь в ответе не зарегистрирован.")
            return
        opponent_display = get_display_name(opponent_user)
    else:
        await message.answer(
            "❌ Неверный формат.\n"
            "Варианты:\n"
            "<code>/duel @username 100</code>\n"
            "<code>/duel 100</code> (в ответ на сообщение)",
            parse_mode=ParseMode.HTML
        )
        return

    bet = money_2(float(bet_str.replace(",", ".")))
    if not (0 < bet <= 1000):
        await message.answer("💰 Сумма должна быть от 1 до 1000 PidorCoins.")
        return

    if initiator.telegram_id == opponent_user.telegram_id:
        await message.answer("🤡 Нельзя драться самому с собой, шизик.")
        return

    # Проверка баланса
    if initiator.balance < bet:
        await message.answer("❌ У вас недостаточно PidorCoins.")
        return
    if opponent_user.balance < bet:
        await message.answer(f"❌ У вашего оппонента недостаточно средств.")
        return

    # Проверка активной дуэли
    duel = await DuelCRUD.get_pending_or_active_duel_by_chat(session, message.chat.id)
    if duel:
        created_at = duel.created_at.replace(tzinfo=UTC) if duel.created_at.tzinfo is None else duel.created_at
        if datetime.now(UTC) - created_at > timedelta(minutes=10):
            await DuelCRUD.cancel_duel_with_refund(session, duel)
            logger.info(f"Old duel {duel.id} in chat {duel.chat_id} was cancelled due to timeout")
        else:
            await message.answer("⚔️ Уже идёт дуэль или кто-то вызван. Подожди завершения.")
            return

    # Создание дуэли
    chat = await ChatCRUD.get_chat(session, message.chat.id)
    initiator.balance = money_2(initiator.balance - bet)
    duel = await DuelCRUD.create_duel(session, chat.id, initiator.id, opponent_user.id, bet)
    await CurrencyTransactionCRUD.create_transaction(session, initiator.id, bet, "duel initiator bet")
    logger.info(
        f"{initiator.telegram_id} initiated a duel with {opponent_user.telegram_id} for {bet:.2f} coins in chat {message.chat.id}"
    )
    await session.commit()

    await message.answer(
        f"⚔️{get_display_name(initiator)} "
        f"вызвал {opponent_display} на дуэль на сумму {bet:.2f} 🪙 PidorCoins!\n\n"
        "/accept_duel - принять дуэль\n"
        "/cancel_duel - отклонить дуэль",
        parse_mode=ParseMode.HTML
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
        logger.info(f"Duel {duel.id} cancelled due to opponent ({get_display_name(duel.opponent)}) lacking funds")
        return

    duel.opponent.balance = money_2(duel.opponent.balance - duel.amount)
    duel.status = DuelStatus.FINISHED
    duel.accepted_at = datetime.now(UTC)

    initiator = duel.initiator
    opponent = duel.opponent
    winner = choice([initiator, opponent])
    loser = opponent if winner == initiator else initiator
    duel.winner_id = winner.id

    commission = 0.05
    payout = money_2(duel.amount * 2 * (1 - commission))
    winner.balance = money_2(winner.balance + payout)

    await CurrencyTransactionCRUD.create_transaction(session, duel.opponent.id, duel.amount, "duel opponent bet")
    await CurrencyTransactionCRUD.create_transaction(session, winner.id, payout, "duel winner payout")
    await session.commit()

    winner_username = winner.username
    loser_username = initiator.username if winner == opponent else opponent.username

    logger.info(
        f"Duel {duel.id} accepted by {get_display_name(duel.opponent)} — Winner: {get_display_name(winner)}, Loser: {get_display_name(loser)}, Payout: {payout:.2f}")

    await message.bot.send_message(message.chat.id, "🔍Поиск победителя...")
    duel_fight_message = await AI.get_response("", AIPromt.DUEL_WINNER_CHOICE_PROMPT)
    await asyncio.sleep(2)
    await message.bot.send_message(message.chat.id, duel_fight_message.format(winner=winner_username, loser=loser_username))
    await message.answer(
        f"⚔️ Дуэль завершена!\n"
        f"🏆 Победил: <b>{get_display_name(winner)}</b>\n"
        f"☠️ Проиграл: {get_display_name(loser)}\n"
        f"💰 Выплата: {payout:.2f} PidorCoins (комиссия {int(commission * 100)}%)",
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

    logger.info(f"{message.from_user.username} cancelled duel {duel.id} in chat {message.chat.id}")

    opponent_username = duel.opponent.username if duel.opponent else "неизвестный"
    await message.answer(
        f"❌ Дуэль с @{opponent_username} отменена.\n🪙 Ставка возвращена на баланс."
    )
