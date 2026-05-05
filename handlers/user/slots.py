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
from database.money_format import money_2
from handlers.utils.slots_logic import (
    MULT_PAIR_ADJACENT,
    MULT_SANDWICH,
    MULT_TRIPLE_BAR,
    MULT_TRIPLE_GRAPE,
    MULT_TRIPLE_LEMON,
    MULT_TRIPLE_SEVEN,
    get_slots_and_multiplier,
)
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
        bet = money_2(float(bet_str.replace(",", ".")))
        if not (0 < bet <= 5000):
            await message.answer("💰 Сумма должна быть от 1 до 5000 🪙PidorCoins. Или вместо числа allin")
            return
    except ValueError:
        bet = money_2(user.balance)
    is_all_in = bet_str == "allin"
    if is_all_in and not bet:
        await message.answer("❌ У вас недостаточно 🪙PidorCoins для all in")
    if bet > user.balance:
        await message.answer("❌ У вас недостаточно 🪙PidorCoins.")
        return
    user.balance = money_2(user.balance - bet)
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
    gross_win = money_2(bet * multiplier)
    reaction_msg = ""
    m = multiplier
    if m == 0:
        reaction_msg = "Ноль иксов? Братанчик, даже пидорасов будут уважать больше чем тебя! СРОЧНО ДОДЕП!! 😂💔"
        if is_all_in:
            reaction_msg = "Ебать ты лох🫵🫵🫵🫵, депнул хату и проебал ХАХАХАХ"
    elif m == MULT_SANDWICH:
        reaction_msg = "Пара по краям — скромно, но в плюс. Маленький пидорас тоже пидорас."
    elif m == MULT_PAIR_ADJACENT:
        reaction_msg = "Два подряд — уже неплохо, казино чуть побледнело."
    elif m == MULT_TRIPLE_LEMON:
        reaction_msg = "Три лимона — базовый кефирчик, зато стабильно."
    elif m == MULT_TRIPLE_GRAPE:
        reaction_msg = "Три винограда — уже можно похвастаться в чате."
    elif m == MULT_TRIPLE_BAR:
        reaction_msg = "Три бара — ты буквально выбил уважение у однорукого бандита."
    elif m == MULT_TRIPLE_SEVEN:
        reaction_msg = await AI.get_response("", ai_prompt=AIPromt.JACKPOT_REACT_PROMPT.format(
            gross_win=f"{gross_win:.2f}"))
    commission = money_2(gross_win * commission_percent / 100)
    net_win = money_2(gross_win - commission)
    if gross_win != 0:
        user.balance = money_2(user.balance + net_win)
        await CurrencyTransactionCRUD.create_transaction(session, user.id, net_win, "slots win")
        await session.commit()
    await message.answer(
        f"🎰 Результат: {slots_display}\n\n"
        f"💰 Ставка: {bet:.2f}\n"
        f"🎯 Выигрыш: {gross_win:.2f} (x{multiplier:.2f})\n"
        f"💸 Комиссия {commission_percent}%: -{commission:.2f}\n"
        f"🧾 Итог: +{net_win:.2f}\n\n"
        f"📦 Баланс: {user.balance:.2f} 🪙PidorCoins"
        f"\n\n{reaction_msg}"
    )
