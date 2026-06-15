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
        f"<b>⚔️ Дуэли:</b>\n"
        f"🏆 Побед в дуэлях: <b>{duel_wins}</b>\n"
        f"📤 Поставлено: -{duel_bet:.2f} 🪙\n"
        f"📥 Выиграно (после комиссии): +{duel_payout:.2f} 🪙\n"
        f"📈 Чистый профит: {duel_profit:+.2f} 🪙\n"
        f"<b>🎰 Слоты:</b>\n"
        f"📤 Поставлено: -{slot_bet:.2f} 🪙\n"
        f"📥 Выиграно (после комиссии): +{slot_win:.2f} 🪙\n"
        f"📈 Чистый профит: {slot_profit:+.2f} 🪙\n",

        # f"<b>🧠 Навыки:</b>\n{skills_text}",
        parse_mode=ParseMode.HTML
    )
