import asyncio
import re

from aiogram import Router
from aiogram.enums import DiceEmoji
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import AIPrompt
from config.constants import CommandText
from database.repositories.currency_transaction_repository import CurrencyTransactionRepository
from database.repositories.user_repository import UserRepository
from database.transaction_reasons import TransactionReason
from database.money_format import money_2
from services.slots_service import (
    MULT_PAIR_ADJACENT,
    MULT_SANDWICH,
    MULT_TRIPLE_BAR,
    MULT_TRIPLE_GRAPE,
    MULT_TRIPLE_LEMON,
    MULT_TRIPLE_SEVEN,
    SLOTS_COMMISSION_PERCENT,
    calculate_slots_payout,
    get_slots_and_multiplier,
    parse_slots_bet,
    validate_slots_bet,
)
from logger import setup_logger
from services.ai_service import AIService

logger = setup_logger(__name__)

router = Router()


@router.message(Command("slots"))
async def cmd_slots(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        logger.info("Update data rejected: private chat")
        return
    user = await UserRepository.get_user_by_telegram_id(session, message.from_user.id, message.chat.id)
    if user is None:
        await message.reply("Вы ещё не зарегистрированы в этом чате. Пропишите /reg")
        return
    pattern = r"^/slots(?:@[^\s]+)?\s+(allin|\d+(?:[.,]\d{1,2})?)$"
    match = re.match(pattern, (message.text or "").strip(), re.IGNORECASE)
    if not match:
        await message.answer("❌ Неверный формат.\nИспользуй: <code>/slots *ставка* </code>\n\nИли <code>/slots allin </code>", parse_mode="HTML")
        return
    bet_str, = match.groups()
    bet, is_all_in = parse_slots_bet(bet_str, user.balance)
    validation_error = validate_slots_bet(bet, user.balance, is_all_in)
    if validation_error:
        await message.answer(validation_error)
        return

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
    payout = calculate_slots_payout(bet, multiplier)
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
        reaction_msg = await AIService.get_response("", ai_prompt=AIPrompt.JACKPOT_REACT_PROMPT.format(
            gross_win=f"{payout.gross_win:.2f}"))
    user.balance = money_2(user.balance - bet)
    await CurrencyTransactionRepository.create_transaction(session, user.id, bet, TransactionReason.SLOTS_BET)
    if payout.gross_win != 0:
        user.balance = money_2(user.balance + payout.net_win)
        await CurrencyTransactionRepository.create_transaction(session, user.id, payout.net_win, TransactionReason.SLOTS_WIN)
    await session.commit()
    await message.answer(
        f"🎰 Результат: {slots_display}\n\n"
        f"💰 Ставка: {bet:.2f}\n"
        f"🎯 Выигрыш: {payout.gross_win:.2f} (x{multiplier:.2f})\n"
        f"💸 Комиссия {SLOTS_COMMISSION_PERCENT}%: -{payout.commission:.2f}\n"
        f"🧾 Итог: +{payout.net_win:.2f}\n\n"
        f"📦 Баланс: {user.balance:.2f} 🪙PidorCoins"
        f"\n\n{reaction_msg}"
    )
