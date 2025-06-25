import asyncio
import re
from datetime import datetime, UTC, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import CommandText
from database.crud import UserCRUD, DuelCRUD, ChatCRUD, CurrencyTransactionCRUD
from database.models import DuelStatus
from logger import setup_logger
from services.duel_logic import wait_for_acceptance, schedule_duel_resolution

router = Router()
logger = setup_logger(__name__)

@router.message(Command("duel"))
async def cmd_duel(message: Message, session: AsyncSession):
    # Проверка, что это группа
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return

    # Извлекаем username и сумму
    pattern = r"/duel\s+@(\w+)\s+(\d+(?:[.,]\d{1,2})?)"
    match = re.match(pattern, message.text.strip())

    if not match:
        await message.answer("Неверный формат. Используйте: /duel @username 100")
        return
    username_opponent = match.group(1)
    amount = float(match.group(2))
    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.")
        return
    if amount > 1000:
        await message.answer("Сумма не должна превышать 1000 PidorCoins.")
        return
    if username_opponent == message.from_user.username:
        await message.answer("Нельзя драться самому с собой")
        return
    initiator = await UserCRUD.get_user_by_username(session, message.from_user.username, message.chat.id)
    if not initiator:
        await message.answer("Вы не зарегистрированы в чате")
        return
    opponent = await UserCRUD.get_user_by_username(session, username_opponent, message.chat.id)
    if not opponent:
        await message.answer(f"Пользователь {username_opponent} не зарегистрирован в базе")
        return
    if initiator.balance < amount:
        await message.answer("Недостаточно средств")
        return
    if opponent.balance < amount:
        await message.answer(f"У пользователя {username_opponent} недостаточно средств")
        return
    duel = await DuelCRUD.get_pending_or_active_duel_by_chat(session, message.chat.id)
    if duel:
        created_at = duel.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if datetime.now(UTC) - created_at > timedelta(minutes=10):
            await DuelCRUD.cancel_duel_with_refund(session, duel)
            logger.info(f"Cancelled duel {duel.id} in chat {duel.chat_id} due to timeout")
        else:
            await message.answer("Дуэль уже идет в этом чате, или кого-то вызвали на нее")
            return
    chat = await ChatCRUD.get_chat(session, message.chat.id)
    initiator.balance -= amount
    duel = await DuelCRUD.create_duel(session, chat.id, initiator.id, opponent.id, amount)
    await CurrencyTransactionCRUD.create_transaction(session, initiator.id, amount, "duel initiator bet")
    await session.commit()
    await message.answer(f"@{message.from_user.username} по пидорски вызвал на дуэль @{username_opponent} на сумму {amount} PidorCoins")
    asyncio.create_task(wait_for_acceptance(message.bot, session, duel.id, message.chat.id))

@router.message(Command("accept_duel"))
async def cmd_accept_duel(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return
    duel = await DuelCRUD.get_pending_confirmation(session, message.chat.id, message.from_user.id)
    if not duel:
        await message.answer("Для тебя нет активных дуэлей")
        return
    if duel.opponent.balance < duel.amount:
        await message.answer("У вас недостаточно средств для принятия дуэли")
        duel.status = DuelStatus.CANCELLED
        return
    duel.opponent.balance -= duel.amount
    duel.status = DuelStatus.ACTIVE
    duel.accepted_at = datetime.now(UTC)
    await CurrencyTransactionCRUD.create_transaction(session, duel.opponent.id, duel.amount, "duel opponent bet")
    await session.commit()
    await message.answer("Дуэль принята, начало через 5мин, начат прием ставок")
    asyncio.create_task(schedule_duel_resolution(message.bot, session, duel.id))