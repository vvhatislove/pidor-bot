import os
import subprocess
from html import escape
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from aiogram import Router
from aiogram import F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import case, delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import config
from database.models import Chat, Cooldown, CurrencyTransaction, User
from database.money_format import money_2
from database.repositories.chat_repository import ChatRepository
from database.repositories.cooldown_repository import CooldownRepository
from database.repositories.currency_transaction_repository import CurrencyTransactionRepository
from database.repositories.user_repository import UserRepository
from database.transaction_reasons import (
    TransactionReason,
    is_transaction_debit,
    normalize_transaction_reason,
    transaction_display_name,
)
from handlers.formatting import get_display_name
from logger import setup_logger
from services.ai_response_buffer import ai_response_buffer
from services.backup_service import create_backup_zip
from services.time_service import format_local_datetime

router = Router()
logger = setup_logger(__name__)

DEFAULT_LIMIT = 10
MAX_LIMIT = 50
CHATS_CALLBACK_PREFIX = "admin_chats"


@dataclass(frozen=True)
class ChatContext:
    telegram_id: int
    chat: Chat
    rest: list[str]


def _is_admin(message: Message) -> bool:
    return message.from_user.id == config.ADMIN_ID


async def _admin_only(message: Message) -> bool:
    if _is_admin(message):
        return True
    await message.answer("Недостаточно прав.")
    return False


async def _private_admin_only(message: Message) -> bool:
    if not await _admin_only(message):
        return False
    if message.chat.type != "private":
        await message.answer("Эту админскую команду нужно вызывать в ЛС боту.")
        return False
    return True


def _parts(message: Message) -> list[str]:
    return (message.text or "").split()[1:]


def _parse_limit(value: str | None, default: int = DEFAULT_LIMIT) -> int:
    if not value:
        return default
    try:
        return max(1, min(int(value), MAX_LIMIT))
    except ValueError:
        return default


def _parse_page_args(parts: list[str]) -> tuple[int, int]:
    try:
        page = int(parts[0]) if parts else 1
    except ValueError:
        page = 1
    try:
        per_page = int(parts[1]) if len(parts) > 1 else 10
    except ValueError:
        per_page = 10
    return max(page, 1), max(1, min(per_page, MAX_LIMIT))


async def _resolve_chat_context(message: Message, session: AsyncSession) -> ChatContext | None:
    parts = _parts(message)
    if message.chat.type == "private":
        if not parts:
            await message.answer("Укажи chat_id.\nПример: <code>/chat_info -100123</code>", parse_mode="HTML")
            return None
        try:
            chat_telegram_id = int(parts[0])
        except ValueError:
            await message.answer("Первым аргументом должен быть chat_id.")
            return None
        rest = parts[1:]
    else:
        chat_telegram_id = message.chat.id
        rest = parts

    chat = await ChatRepository.get_chat(session, chat_telegram_id)
    if not chat:
        await message.answer(f"Чат <code>{chat_telegram_id}</code> не найден в БД.", parse_mode="HTML")
        return None
    return ChatContext(chat_telegram_id, chat, rest)


async def _resolve_user_from_context(
        message: Message,
        session: AsyncSession,
        context: ChatContext,
        username_arg: str | None,
) -> User | None:
    if not username_arg:
        await message.answer("Укажи username.\nПример: <code>/user_info @username</code>", parse_mode="HTML")
        return None
    user = await UserRepository.get_user_by_username(session, username_arg, context.telegram_id)
    if not user:
        await message.answer(f"Пользователь {username_arg} не найден в этом чате.")
        return None
    return user


def _user_label(user: User) -> str:
    return user.username and f"@{escape(user.username)}" or f"{escape(user.first_name)} ({user.telegram_id})"


def _format_transaction(tx: CurrencyTransaction) -> str:
    sign = "-" if is_transaction_debit(tx.reason) else "+"
    reason = transaction_display_name(tx.reason)
    created = format_local_datetime(tx.created_at, "%d.%m %H:%M")
    return f"{created} | {sign}{tx.amount:.2f} 🪙 | {reason}"


async def _chat_transactions(session: AsyncSession, chat_id: int, limit: int) -> list[CurrencyTransaction]:
    result = await session.execute(
        select(CurrencyTransaction)
        .join(User, CurrencyTransaction.user_id == User.id)
        .where(User.chat_id == chat_id)
        .order_by(CurrencyTransaction.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def _all_chat_users(session: AsyncSession, chat_id: int) -> list[User]:
    result = await session.execute(select(User).where(User.chat_id == chat_id))
    return list(result.scalars().all())


async def _top_by_metric(
        session: AsyncSession,
        chat_id: int,
        reason_prefix: str,
        payout_reason: str,
        bet_reasons: set[str],
) -> list[tuple[User, float]]:
    users = await _all_chat_users(session, chat_id)
    result = await session.execute(
        select(CurrencyTransaction)
        .join(User, CurrencyTransaction.user_id == User.id)
        .where(User.chat_id == chat_id)
    )
    by_user: dict[int, float] = defaultdict(float)
    for tx in result.scalars().all():
        reason = normalize_transaction_reason(tx.reason)
        if reason == payout_reason:
            by_user[tx.user_id] += tx.amount
        elif reason in bet_reasons:
            by_user[tx.user_id] -= tx.amount
        elif reason_prefix and reason.startswith(reason_prefix):
            by_user.setdefault(tx.user_id, 0.0)
    ranked = [(user, money_2(by_user.get(user.id, 0.0))) for user in users if user.id in by_user]
    return sorted(ranked, key=lambda item: item[1], reverse=True)


@router.message(Command("admin_stats", ignore_case=True, ignore_mention=True))
async def cmd_admin_stats(message: Message, session: AsyncSession):
    if not await _private_admin_only(message):
        return

    chat_count = await session.scalar(select(func.count(Chat.id)))
    user_count = await session.scalar(select(func.count(User.id)))
    active_count = await session.scalar(select(func.count(User.id)).where(User.is_active.is_(True)))
    tx_count = await session.scalar(select(func.count(CurrencyTransaction.id)))
    balance_sum = await session.scalar(select(func.coalesce(func.sum(User.balance), 0.0)))

    await message.answer(
        "📊 <b>Админ-статистика</b>\n"
        f"Чатов: <b>{chat_count}</b>\n"
        f"Пользователей: <b>{user_count}</b>\n"
        f"Активных в розыгрыше: <b>{active_count}</b>\n"
        f"Неактивных: <b>{(user_count or 0) - (active_count or 0)}</b>\n"
        f"Транзакций: <b>{tx_count}</b>\n"
        f"Баланс в системе: <b>{money_2(balance_sum or 0):.2f}</b> 🪙",
        parse_mode="HTML",
    )


@router.message(Command("chats", ignore_case=True, ignore_mention=True))
async def cmd_chats(message: Message, session: AsyncSession):
    if not await _private_admin_only(message):
        return

    page, per_page = _parse_page_args(_parts(message))
    text_value, keyboard = await _build_chats_page(session, page, per_page)
    await message.answer(text_value, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith(f"{CHATS_CALLBACK_PREFIX}:"))
async def cb_chats_page(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    try:
        _, page_raw, per_page_raw = (callback.data or "").split(":", maxsplit=2)
        page = int(page_raw)
        per_page = int(per_page_raw)
    except ValueError:
        await callback.answer("Некорректная страница.", show_alert=True)
        return

    text_value, keyboard = await _build_chats_page(session, page, per_page)
    await callback.message.edit_text(text_value, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


async def _build_chats_page(session: AsyncSession, page: int, per_page: int) -> tuple[str, InlineKeyboardMarkup]:
    total_chats = await session.scalar(select(func.count(Chat.id))) or 0
    per_page = max(1, min(per_page, MAX_LIMIT))
    total_pages = max((total_chats + per_page - 1) // per_page, 1)
    page = min(page, total_pages)
    offset = (page - 1) * per_page

    result = await session.execute(
        select(
            Chat.id,
            Chat.telegram_chat_id,
            Chat.title,
            func.count(User.id).label("users_count"),
            func.coalesce(func.sum(User.balance), 0.0).label("balance_sum"),
            func.coalesce(func.sum(case((User.is_active.is_(True), 1), else_=0)), 0).label("active_count"),
        )
        .outerjoin(User, User.chat_id == Chat.id)
        .group_by(Chat.id)
        .order_by(Chat.id)
        .offset(offset)
        .limit(per_page)
    )

    rows = [
        f"💬 <b>Чаты</b> — страница <b>{page}/{total_pages}</b>",
        f"Всего чатов: <b>{total_chats}</b>\n",
    ]
    for index, row in enumerate(result.all(), offset + 1):
        title = escape(row.title or "без названия")
        rows.append(
            f"{index}. Название: <b>{title}</b>\n"
            f"ID: <code>{row.telegram_chat_id}</code> | "
            f"участников: <b>{row.users_count}</b> "
            f"(активных: <b>{row.active_count}</b>) | "
            f"{money_2(row.balance_sum):.2f} 🪙"
        )

    keyboard = _chats_keyboard(page, total_pages, per_page)
    return "\n".join(rows), keyboard


def _chats_keyboard(page: int, total_pages: int, per_page: int) -> InlineKeyboardMarkup:
    prev_page = max(page - 1, 1)
    next_page = min(page + 1, total_pages)
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="‹",
            callback_data=f"{CHATS_CALLBACK_PREFIX}:{prev_page}:{per_page}" if page > 1 else f"{CHATS_CALLBACK_PREFIX}:{page}:{per_page}",
        ),
        InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data=f"{CHATS_CALLBACK_PREFIX}:{page}:{per_page}"),
        InlineKeyboardButton(
            text="›",
            callback_data=f"{CHATS_CALLBACK_PREFIX}:{next_page}:{per_page}" if page < total_pages else f"{CHATS_CALLBACK_PREFIX}:{page}:{per_page}",
        ),
    ]])


@router.message(Command("economy_stats", ignore_case=True, ignore_mention=True))
async def cmd_economy_stats(message: Message, session: AsyncSession):
    if not await _private_admin_only(message):
        return

    transactions = await CurrencyTransactionRepository.get_all_transactions(session)
    totals: dict[str, float] = defaultdict(float)
    for tx in transactions:
        totals[normalize_transaction_reason(tx.reason)] += tx.amount

    rows = ["💰 <b>Экономика</b>"]
    for reason, amount in sorted(totals.items()):
        rows.append(f"{transaction_display_name(reason)}: <b>{money_2(amount):.2f}</b> 🪙")
    await message.answer("\n".join(rows), parse_mode="HTML")


@router.message(Command("ai_status", ignore_case=True, ignore_mention=True))
async def cmd_ai_status(message: Message):
    if not await _private_admin_only(message):
        return

    buffer_sizes = {key: len(buffer) for key, buffer in ai_response_buffer._buffers.items()}
    rows = [
        "🧠 <b>AI status</b>",
        f"Model: <code>{config.AI_MODEL or config.OPENROUTER_CHAT_MODEL or 'default'}</code>",
        f"OpenRouter key: <b>{'есть' if bool(config.OPENROUTER_API_KEY.strip()) else 'нет'}</b>",
        f"Buffer target: <b>{config.AI_BUFFER_TARGET_SIZE}</b>",
    ]
    rows.extend(f"{key}: <b>{value}</b>" for key, value in buffer_sizes.items())
    await message.answer("\n".join(rows), parse_mode="HTML")


@router.message(Command("db_status", ignore_case=True, ignore_mention=True))
async def cmd_db_status(message: Message, session: AsyncSession):
    if not await _private_admin_only(message):
        return

    revision = await session.scalar(text("select version_num from alembic_version limit 1"))
    db_path = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "", 1)
    path = Path(db_path)
    size = path.stat().st_size if path.exists() else 0
    await message.answer(
        "🗄 <b>DB status</b>\n"
        f"URL: <code>{config.DATABASE_URL}</code>\n"
        f"Alembic: <code>{revision}</code>\n"
        f"Файл: <code>{path}</code>\n"
        f"Размер: <b>{size / 1024:.1f} KB</b>",
        parse_mode="HTML",
    )


@router.message(Command("health", ignore_case=True, ignore_mention=True))
async def cmd_health(message: Message, session: AsyncSession):
    if not await _private_admin_only(message):
        return

    await session.scalar(select(func.count(Chat.id)))
    await message.answer(
        "✅ <b>Health</b>\n"
        "Bot: <b>ok</b>\n"
        "DB: <b>ok</b>\n"
        f"OpenRouter key: <b>{'ok' if config.OPENROUTER_API_KEY.strip() else 'missing'}</b>\n"
        f"AI buffer: <b>{sum(len(buffer) for buffer in ai_response_buffer._buffers.values())}</b>",
        parse_mode="HTML",
    )


@router.message(Command("backup_now", ignore_case=True, ignore_mention=True))
async def cmd_backup_now(message: Message):
    if not await _private_admin_only(message):
        return

    backup_path = create_backup_zip()
    await message.answer_document(FSInputFile(backup_path), caption="🛡️ Backup file")


@router.message(Command("version", ignore_case=True, ignore_mention=True))
async def cmd_version(message: Message):
    if not await _private_admin_only(message):
        return

    def git_value(*args: str) -> str:
        try:
            return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()
        except Exception:
            return "unknown"

    await message.answer(
        "🧬 <b>Version</b>\n"
        f"Branch: <code>{git_value('rev-parse', '--abbrev-ref', 'HEAD')}</code>\n"
        f"Commit: <code>{git_value('rev-parse', '--short', 'HEAD')}</code>\n"
        f"Message: <code>{git_value('log', '-1', '--pretty=%s')}</code>",
        parse_mode="HTML",
    )


@router.message(Command("chat_info", ignore_case=True, ignore_mention=True))
async def cmd_chat_info(message: Message, session: AsyncSession):
    if not await _admin_only(message):
        return
    context = await _resolve_chat_context(message, session)
    if not context:
        return

    users = await _all_chat_users(session, context.chat.id)
    active = [user for user in users if user.is_active]
    cooldown = await CooldownRepository.get_cooldown(session, context.telegram_id)
    today_pidor = await CooldownRepository.get_cooldown_pidor_user(session, context.telegram_id)
    last_activated = format_local_datetime(cooldown.last_activated) if cooldown else "нет"
    await message.answer(
        "💬 <b>Chat info</b>\n"
        f"Title: <b>{escape(context.chat.title)}</b>\n"
        f"Telegram ID: <code>{context.chat.telegram_chat_id}</code>\n"
        f"DB ID: <code>{context.chat.id}</code>\n"
        f"Auto pidor: <b>{'on' if context.chat.auto_pidor else 'off'}</b>\n"
        f"Участников: <b>{len(users)}</b>\n"
        f"Активных: <b>{len(active)}</b>\n"
        f"Сегодня: <b>{get_display_name(today_pidor) if today_pidor else 'не выбран/не сохранен'}</b>\n"
        f"Последний запуск: <b>{last_activated}</b>",
        parse_mode="HTML",
    )


@router.message(Command("today_pidor", ignore_case=True, ignore_mention=True))
async def cmd_today_pidor(message: Message, session: AsyncSession):
    if not await _admin_only(message):
        return
    context = await _resolve_chat_context(message, session)
    if not context:
        return
    today_pidor = await CooldownRepository.get_cooldown_pidor_user(session, context.telegram_id)
    await message.answer(
        f"Сегодня в чате <b>{escape(context.chat.title)}</b>: "
        f"{get_display_name(today_pidor) if today_pidor else '<b>не выбран/не сохранен</b>'}",
        parse_mode="HTML",
    )


@router.message(Command("reset_pidor_today", ignore_case=True, ignore_mention=True))
async def cmd_reset_pidor_today(message: Message, session: AsyncSession):
    if not await _private_admin_only(message):
        return
    context = await _resolve_chat_context(message, session)
    if not context:
        return
    result = await session.execute(delete(Cooldown).where(Cooldown.chat_id == context.chat.id))
    await session.commit()
    await message.answer(
        f"Сброшено cooldown-записей для <b>{escape(context.chat.title)}</b>: {result.rowcount}",
        parse_mode="HTML",
    )


@router.message(Command("active_users", "inactive_users", ignore_case=True, ignore_mention=True))
async def cmd_participation_users(message: Message, session: AsyncSession):
    if not await _admin_only(message):
        return
    context = await _resolve_chat_context(message, session)
    if not context:
        return
    want_active = (message.text or "").split()[0].lower().startswith("/active_users")
    users = [user for user in await _all_chat_users(session, context.chat.id) if user.is_active is want_active]
    title = "Активные участники" if want_active else "Неактивные участники"
    lines = [f"{title} <b>{escape(context.chat.title)}</b>: {len(users)}"]
    lines.extend(f"{index}. {_user_label(user)} | {user.balance:.2f} 🪙" for index, user in enumerate(users[:MAX_LIMIT], 1))
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("top_balance", "top_pidor", ignore_case=True, ignore_mention=True))
async def cmd_top_users(message: Message, session: AsyncSession):
    if not await _admin_only(message):
        return
    context = await _resolve_chat_context(message, session)
    if not context:
        return
    users = await _all_chat_users(session, context.chat.id)
    command = (message.text or "").split()[0].lower()
    if command.startswith("/top_balance"):
        ranked = sorted(users, key=lambda user: user.balance, reverse=True)
        lines = [f"🏦 <b>Топ баланса: {escape(context.chat.title)}</b>"]
        lines.extend(f"{i}. {_user_label(user)} — {user.balance:.2f} 🪙" for i, user in enumerate(ranked[:10], 1))
    else:
        ranked = sorted(users, key=lambda user: user.pidor_count, reverse=True)
        lines = [f"🐓 <b>Топ пидора дня: {escape(context.chat.title)}</b>"]
        lines.extend(f"{i}. {_user_label(user)} — {user.pidor_count} раз(а)" for i, user in enumerate(ranked[:10], 1))
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("top_slots", "top_duels", ignore_case=True, ignore_mention=True))
async def cmd_top_games(message: Message, session: AsyncSession):
    if not await _admin_only(message):
        return
    context = await _resolve_chat_context(message, session)
    if not context:
        return
    command = (message.text or "").split()[0].lower()
    if command.startswith("/top_slots"):
        ranked = await _top_by_metric(
            session,
            context.chat.id,
            "slots_",
            TransactionReason.SLOTS_WIN,
            {TransactionReason.SLOTS_BET},
        )
        title = "🎰 Топ слотов"
    else:
        ranked = await _top_by_metric(
            session,
            context.chat.id,
            "duel_",
            TransactionReason.DUEL_WINNER_PAYOUT,
            {TransactionReason.DUEL_INITIATOR_BET, TransactionReason.DUEL_OPPONENT_BET},
        )
        title = "⚔️ Топ дуэлей"
    lines = [f"{title}: <b>{escape(context.chat.title)}</b>"]
    lines.extend(f"{i}. {_user_label(user)} — {profit:+.2f} 🪙" for i, (user, profit) in enumerate(ranked[:10], 1))
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("chat_transactions", ignore_case=True, ignore_mention=True))
async def cmd_chat_transactions(message: Message, session: AsyncSession):
    if not await _admin_only(message):
        return
    context = await _resolve_chat_context(message, session)
    if not context:
        return
    limit = _parse_limit(context.rest[0] if context.rest else None)
    transactions = await _chat_transactions(session, context.chat.id, limit)
    lines = [f"🧾 <b>Последние транзакции: {escape(context.chat.title)}</b>"]
    for tx in transactions:
        user = await session.get(User, tx.user_id)
        lines.append(f"{_user_label(user)} | {_format_transaction(tx)}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("user_info", ignore_case=True, ignore_mention=True))
async def cmd_user_info(message: Message, session: AsyncSession):
    if not await _admin_only(message):
        return
    context = await _resolve_chat_context(message, session)
    if not context:
        return
    user = await _resolve_user_from_context(message, session, context, context.rest[0] if context.rest else None)
    if not user:
        return
    slot_bet, slot_win, slot_profit = await CurrencyTransactionRepository.get_slot_stats_for_user(session, user.id)
    duel_bet, duel_payout, duel_profit = await CurrencyTransactionRepository.get_duel_stats_for_user(session, user.id)
    await message.answer(
        f"👤 <b>{get_display_name(user)}</b>\n"
        f"Telegram ID: <code>{user.telegram_id}</code>\n"
        f"DB ID: <code>{user.id}</code>\n"
        f"Участие: <b>{'активен' if user.is_active else 'не участвует'}</b>\n"
        f"Баланс: <b>{user.balance:.2f}</b> 🪙\n"
        f"Пидор дня: <b>{user.pidor_count}</b>\n"
        f"Слоты: ставка {slot_bet:.2f}, выигрыш {slot_win:.2f}, профит {slot_profit:+.2f}\n"
        f"Дуэли: ставка {duel_bet:.2f}, выплата {duel_payout:.2f}, профит {duel_profit:+.2f}",
        parse_mode="HTML",
    )


@router.message(Command("transactions", ignore_case=True, ignore_mention=True))
async def cmd_user_transactions(message: Message, session: AsyncSession):
    if not await _admin_only(message):
        return
    context = await _resolve_chat_context(message, session)
    if not context:
        return
    user = await _resolve_user_from_context(message, session, context, context.rest[0] if context.rest else None)
    if not user:
        return
    limit = _parse_limit(context.rest[1] if len(context.rest) > 1 else None)
    transactions = list(await CurrencyTransactionRepository.get_user_transactions(session, user.id))
    transactions.sort(key=lambda tx: tx.created_at, reverse=True)
    lines = [f"🧾 <b>Транзакции {get_display_name(user)}</b>"]
    lines.extend(_format_transaction(tx) for tx in transactions[:limit])
    await message.answer("\n".join(lines), parse_mode="HTML")
