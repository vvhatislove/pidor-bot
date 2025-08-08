import asyncio
import re

from aiogram import Router
from aiogram.enums import DiceEmoji
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import AIPromt
from config.constants import CommandText
from database.CRUD.currency_transaction_crud import CurrencyTransactionCRUD
from database.CRUD.user_crud import UserCRUD
from handlers.utils.slots_logic import get_slots_and_multiplier
from logger import setup_logger
from handlers.utils.AI import AI

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
    pattern = r"^/slots\s+(allin|\d+(?:[.,]\d{1,2})?)$"
    match = re.match(pattern, message.text.strip())
    if not match:
        await message.answer("❌ Неверный формат.\nИспользуй: <code>/slots *ставка* </code>\n\nИли <code>/slots allin </code>", parse_mode="HTML")
        return
    bet_str, = match.groups()
    try:
        bet = float(bet_str.replace(",", "."))
        if not (0 < bet <= 5000):
            await message.answer("💰 Сумма должна быть от 1 до 5000 🪙PidorCoins. Или вместо числа allin")
            return
    except ValueError:
        bet = user.balance
    is_all_in = bet_str is "allin"
    if bet > user.balance:
        await message.answer("❌ У вас недостаточно 🪙PidorCoins.")
        return
    user.balance -= bet
    await CurrencyTransactionCRUD.create_transaction(session, user.id, bet, "slots bet")
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
            if is_all_in:
                reaction_msg = "\n\n Ебать ты лох🫵🫵🫵🫵, депнул хату и проебал ХАХАХАХ"
        case 1.5:
            reaction_msg = "1.5x, ну соболезную, лучше чем хуй в жопе, правда?"
        case 2:
            reaction_msg = "Два икса? Два пидораса таки и делают друг друга пидорасами! 😂👬"
        case 5:
            reaction_msg = "5 иксов? Ты не просто пидор, ты грандмастер голубизма с карамельным шлейфом! 👑😈"
        case 10:
            reaction_msg = await AI.get_response("", ai_prompt=AIPromt.JACKPOT_REACT_PROMPT.format(
                gross_win=gross_win))
    commission = round(gross_win * commission_percent / 100, 2)
    net_win = round(gross_win - commission, 2)
    if gross_win != 0:
        user.balance += net_win
        await CurrencyTransactionCRUD.create_transaction(session, user.id, net_win, "slots win")
        await session.commit()
    await message.answer(
        f"🎰 Результат: {slots_display}\n\n"
        f"💰 Ставка: {bet}\n"
        f"🎯 Выигрыш: {gross_win} (x{multiplier})\n"
        f"💸 Комиссия {commission_percent}%: -{commission}\n"
        f"🧾 Итог: +{net_win}\n\n"
        f"📦 Баланс: {round(user.balance, 2)} 🪙PidorCoins"
        f"\n\n{reaction_msg}"
    )
