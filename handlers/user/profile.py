from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import CommandText
from database.CRUD.duel_crud import DuelCRUD
from database.CRUD.currency_transaction_crud import CurrencyTransactionCRUD
from database.CRUD.user_crud import UserCRUD

router = Router()


@router.message(Command("profile"))
async def cmd_profile(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return

    user = await UserCRUD.get_user_by_username(session, message.from_user.username, message.chat.id)
    if not user:
        await message.answer("🚫 Вы не зарегистрированы в этом чате.")
        return

    duel_wins = await DuelCRUD.count_duel_wins(session, user.id)
    duel_bet, duel_payout, duel_profit = await CurrencyTransactionCRUD.get_duel_stats_for_user(session, user.id)
    slot_bet, slot_win, slot_profit = await CurrencyTransactionCRUD.get_slot_stats_for_user(session, user.id)

    # Список навыков
    # skills_text = "—"
    # if user.user_skills:
    #     skills_text = "\n".join(
    #         f"• {s.skill.name} — уровень {s.level}" for s in user.user_skills
    #     )

    reg_date = user.registration_date.strftime('%d.%m.%Y')

    await message.answer(
        f"<b>👤 Профиль @{user.username or user.first_name}</b>\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"📆 Зарегистрирован: {reg_date}\n"
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
        parse_mode="HTML"
    )
