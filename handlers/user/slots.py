import asyncio
import re

from aiogram import Router
from aiogram.enums import DiceEmoji
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import AIPromt
from config.constants import CommandText
from database.crud import UserCRUD
from logger import setup_logger
from services.ai_service import AIService
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
        await message.answer("💰 Сумма должна быть от 1 до 1000 🪙PidorCoins.")
        return
    if bet > user.balance:
        await message.answer("❌ У вас недостаточно 🪙PidorCoins.")
        return
    user.balance -= bet
    await session.commit()
    msg = await message.answer_dice(emoji=DiceEmoji.SLOT_MACHINE)
    slots, multiplier = get_slots_and_multiplier(msg.dice.value)
    await asyncio.sleep(2)
    emojis = {
        "bar": "BAR",
        "grape": "🍇",
        "lemon": "🍋",
        "seven": "7️⃣"
    }
    slots_display = " | ".join(emojis.get(s, s) for s in slots)
    commission_percent: float = 2.0
    gross_win = bet * multiplier
    reaction_msg = ""
    match multiplier:
        case 0:
            reaction_msg = "Ноль иксов? Братанчик, даже пидорасов будут уважать больше чем тебя! СРОЧНО ДОДЕП!! 😂💔"
        case 2:
            reaction_msg = "Два икса? Два пидораса таки и делают друг друга пидорасами! 😂👬"
        case 5:
            reaction_msg = "Пять иксов! Собралась пидорская пятёрка — это уже не просто пидорасы, а пидорский клан! 😂👑"
        case 10:
            reaction_msg = "Десять иксов? Ты не просто пидор, ты грандмастер голубизма с карамельным шлейфом! 👑😈"
        case 20:
            reaction_msg = "Двадцать иксов? Ты уже на уровне олимпийского пидора, медаль за разорванный пердак точно заслужил! 🏅🌟"
        case 50:
            reaction_msg = await AIService.get_response("", ai_prompt=AIPromt.JACKPOT_REACT_PROMPT.format(gross_win))
    commission = round(gross_win * commission_percent / 100, 2)
    net_win = round(gross_win - commission, 2)
    if gross_win != 0:
        user.balance += net_win + bet
        await session.commit()
    await message.answer(
        f"🎰 Результат: {slots_display}\n\n"
        f"💰 Ставка: {bet}\n"
        f"🎯 Выигрыш: {gross_win} (x{multiplier})\n"
        f"💸 Комиссия {commission_percent}%: -{commission}\n"
        f"🧾 Итог: +{net_win}\n\n"
        f"📦 Баланс: {user.balance} 🪙PidorCoins"
        f"\n\n{reaction_msg}"
    )
