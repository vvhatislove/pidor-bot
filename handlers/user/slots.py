import re

from aiogram import Router
from aiogram.enums import DiceEmoji
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import CommandText
from database.crud import UserCRUD
from logger import setup_logger
from services.slots_logic import get_slots_and_multiplier

logger = setup_logger(__name__)

router = Router()


@router.message(Command("slots"))
async def cmd_slots(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        logger.info("Update data rejected: private chat")
        return
    user = await UserCRUD.get_user_by_telegram_id(session, message.from_user.id, message.chat.id)
    if user is None:
        await message.reply("Вы ещё не зарегистрированы в этом чате. Пропишите /reg")
        return
    pattern = r"^/slots\s+(\d+(?:[.,]\d{1,2})?)$"
    match = re.match(pattern, message.text.strip())
    if not match:
        await message.answer("❌ Неверный формат.\nИспользуй: <code>/slots *ставка* </code>", parse_mode="HTML")
        return
    bet_str, = match.groups()
    bet = float(bet_str.replace(",", "."))
    if not (0 < bet <= 1000):
        await message.answer("💰 Сумма должна быть от 1 до 1000 PidorCoins.")
        return
    if bet > user.balance:
        await message.answer("❌ У вас недостаточно PidorCoins.")
        return
    msg = await message.answer_dice(emoji=DiceEmoji.SLOT_MACHINE)

    slots, multiplier = get_slots_and_multiplier(msg.dice.value)

    await message.answer(f'{multiplier=}')
