import re

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import config
from database.repositories.currency_transaction_repository import CurrencyTransactionRepository
from database.repositories.user_repository import UserRepository
from database.transaction_reasons import admin_add_balance_reason
from database.money_format import money_2
from logger import setup_logger

logger = setup_logger(__name__)

router = Router()

_MAX_ADD = 1_000_000.0


async def _actor_is_admin(session: AsyncSession, message: Message) -> bool:
    if message.from_user.id == config.ADMIN_ID:
        return True
    actor = await UserRepository.get_user_by_telegram_id(
        session, message.from_user.id, message.chat.id
    )
    return bool(actor and actor.is_admin)


@router.message(
    Command(
        "addbalance",
        "addbalnce",
        ignore_case=True,
        ignore_mention=True,
    )
)
async def cmd_add_balance(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer("Эту команду нужно вызывать в группе.")
        return

    if not await _actor_is_admin(session, message):
        await message.reply("Недостаточно прав.")
        return

    # /addbalance …, /addbalnce … (частая опечатка), опционально @BotName в группах
    pattern = (
        r"^/(?:addbalance|addbalnce)(?:@[^\s]+)?\s+"
        r"@?(\w+)\s+(\d+(?:[.,]\d{1,2})?)$"
    )
    m = re.match(pattern, (message.text or "").strip(), re.IGNORECASE)
    if not m:
        await message.answer(
            "Формат: <code>/addbalance @username сумма</code>\n"
            "Пример: <code>/addbalance @vasya 100</code>",
            parse_mode="HTML",
        )
        return

    username_raw, amount_str = m.groups()
    amount = money_2(float(amount_str.replace(",", ".")))
    if not (0 < amount <= _MAX_ADD):
        await message.answer(f"Сумма должна быть от 0.01 до {_MAX_ADD:.2f} 🪙.")
        return

    target = await UserRepository.get_user_by_username(session, username_raw, message.chat.id)
    if target is None:
        await message.answer(
            f"Пользователь @{username_raw.lstrip('@')} не найден в этом чате "
            "(нет регистрации / нет username в Telegram)."
        )
        return

    target.balance = money_2(target.balance + amount)
    await CurrencyTransactionRepository.create_transaction(
        session, target.id, amount, admin_add_balance_reason(message.from_user.id)
    )
    await session.commit()
    logger.info(
        "addbalance: admin_telegram_id=%s target_user_id=%s target_telegram_id=%s chat_id=%s amount=%.2f new_balance=%.2f",
        message.from_user.id,
        target.id,
        target.telegram_id,
        message.chat.id,
        amount,
        target.balance,
    )
    who = f"@{target.username}" if target.username else target.first_name
    await message.reply(
        f"✅ Начислено <b>{amount:.2f}</b> 🪙 пользователю {who} "
        f"(telegram id <code>{target.telegram_id}</code>).\n"
        f"Новый баланс: <b>{target.balance:.2f}</b> 🪙",
        parse_mode="HTML",
    )
