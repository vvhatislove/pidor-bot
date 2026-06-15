from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import CommandText
from database.repositories.duel_repository import DuelRepository
from database.repositories.currency_transaction_repository import CurrencyTransactionRepository
from database.repositories.user_repository import UserRepository
from handlers.formatting import get_display_name
from services.time_service import format_local_datetime

router = Router()


def _amount(value: float) -> str:
    return f"{abs(value):.2f}"


def _profit(value: float) -> str:
    if abs(value) < 0.005:
        return "0.00"
    return f"{value:+.2f}"


@router.message(Command("profile"))
async def cmd_profile(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return

    user = await UserRepository.get_user_by_telegram_id(session, message.from_user.id, message.chat.id)
    if not user:
        await message.answer("🚫 Вы не зарегистрированы в этом чате.")
        return

    duel_wins = await DuelRepository.count_duel_wins(session, user.id)
    duel_bet, duel_payout, duel_profit = await CurrencyTransactionRepository.get_duel_stats_for_user(session, user.id)
    slot_bet, slot_win, slot_profit = await CurrencyTransactionRepository.get_slot_stats_for_user(session, user.id)

    # Список навыков
    # skills_text = "—"
    # if user.user_skills:
    #     skills_text = "\n".join(
    #         f"• {s.skill.name} — уровень {s.level}" for s in user.user_skills
    #     )

    reg_date = format_local_datetime(user.registration_date, '%d.%m.%Y')
    participation_status = "участвует" if user.is_active else "не участвует"

    await message.answer(
        f"<b>👤 Профиль {get_display_name(user)}</b>\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"📆 Зарегистрирован: {reg_date}\n"
        f"🎲 Розыгрыш пидора дня: <b>{participation_status}</b>\n"
        f"💰 Баланс: <b>{user.balance:.2f}</b> PidorCoins\n"
        f"🐓 Был пидором дня: <b>{user.pidor_count}</b> раз(а)\n"
        "----------------\n"
        f"<b>⚔️ Дуэли:</b>\n"
        f"🏆 Побед в дуэлях: <b>{duel_wins}</b>\n"
        f"📤 Поставлено: {_amount(duel_bet)} 🪙\n"
        f"📥 Выиграно (после комиссии): {_amount(duel_payout)} 🪙\n"
        f"📈 Чистый профит: {_profit(duel_profit)} 🪙\n"
        "----------------\n"
        f"<b>🎰 Слоты:</b>\n"
        f"📤 Поставлено: {_amount(slot_bet)} 🪙\n"
        f"📥 Выиграно (после комиссии): {_amount(slot_win)} 🪙\n"
        f"📈 Чистый профит: {_profit(slot_profit)} 🪙\n",

        # f"<b>🧠 Навыки:</b>\n{skills_text}",
        parse_mode=ParseMode.HTML
    )
