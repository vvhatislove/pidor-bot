from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import config
from database.repositories.chat_repository import ChatRepository
from logger import setup_logger

logger = setup_logger(__name__)

router = Router()

ANNOUNCE_CONFIRM_CALLBACK = "announce_update:confirm"
ANNOUNCE_CANCEL_CALLBACK = "announce_update:cancel"
ANNOUNCE_EDIT_CALLBACK = "announce_update:edit"

DEFAULT_UPDATE_ANNOUNCEMENT = (
    "🛠 Обновление бота\n\n"
    "Коротко по изменениям:\n"
    "• Профиль стал читаемее\n"
    "• Появились достижения и награды\n"
    "• Админка получила больше статистики\n"
    "• Исправлены проблемы с балансом и слотами\n\n"
    "Бот уже работает на новой версии."
)

_pending_update_announcements: dict[int, str] = {}


def _announcement_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить во все чаты", callback_data=ANNOUNCE_CONFIRM_CALLBACK),
            ],
            [
                InlineKeyboardButton(text="✏️ Изменить текст", callback_data=ANNOUNCE_EDIT_CALLBACK),
                InlineKeyboardButton(text="❌ Отмена", callback_data=ANNOUNCE_CANCEL_CALLBACK),
            ],
        ]
    )


def _extract_command_payload(message: Message) -> str:
    parts = (message.text or "").split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


async def _send_announcement_to_chats(
    message: Message,
    session: AsyncSession,
    text: str,
    parse_mode: str | None = None,
) -> tuple[int, int]:
    chats = await ChatRepository.get_all_chats(session)
    success, failed = 0, 0

    for chat in chats:
        try:
            send_kwargs = {"parse_mode": parse_mode} if parse_mode else {}
            await message.bot.send_message(chat.telegram_chat_id, text, **send_kwargs)
            success += 1
        except Exception as exc:
            logger.warning(
                "Failed to send update announcement to chat %s (%s): %s",
                chat.telegram_chat_id,
                chat.title,
                exc,
            )
            failed += 1

    return success, failed


@router.message(Command("announce_update", "announceupdate", ignore_case=True, ignore_mention=True))
async def cmd_announce_update(message: Message):
    if message.chat.type != "private":
        await message.answer("Эта команда работает только в ЛС админу.")
        return
    if message.from_user.id != config.ADMIN_ID:
        return

    text = _extract_command_payload(message) or DEFAULT_UPDATE_ANNOUNCEMENT
    _pending_update_announcements[message.from_user.id] = text

    await message.answer(
        "Превью рассылки обновления:\n\n"
        f"{text}\n\n"
        "Отправить это сообщение во все чаты?",
        reply_markup=_announcement_keyboard(),
    )


@router.callback_query(F.data == ANNOUNCE_EDIT_CALLBACK)
async def cb_announce_update_edit(callback: CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(
        "Отправь новый текст так:\n"
        "/announce_update текст сообщения"
    )


@router.callback_query(F.data == ANNOUNCE_CANCEL_CALLBACK)
async def cb_announce_update_cancel(callback: CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    _pending_update_announcements.pop(callback.from_user.id, None)
    await callback.message.edit_text("Рассылка обновления отменена.")
    await callback.answer()


@router.callback_query(F.data == ANNOUNCE_CONFIRM_CALLBACK)
async def cb_announce_update_confirm(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    text = _pending_update_announcements.pop(callback.from_user.id, None)
    if not text:
        await callback.message.edit_text(
            "Нет подготовленного текста рассылки. Сначала вызови /announce_update."
        )
        await callback.answer()
        return

    chats = await ChatRepository.get_all_chats(session)
    if not chats:
        await callback.message.edit_text("Нет чатов для рассылки.")
        await callback.answer()
        return

    success, failed = 0, 0
    for chat in chats:
        try:
            await callback.message.bot.send_message(chat.telegram_chat_id, text)
            success += 1
        except Exception as exc:
            logger.warning(
                "Failed to send update announcement to chat %s (%s): %s",
                chat.telegram_chat_id,
                chat.title,
                exc,
            )
            failed += 1

    await callback.message.edit_text(
        "Рассылка обновления завершена.\n"
        f"Успешно: {success}\n"
        f"Ошибок: {failed}"
    )
    await callback.answer()


@router.message(Command("send_global_message", "sendglobalmessage"))
async def cmd_send_global_message(message: Message, session: AsyncSession):
    if message.chat.type != "private":
        logger.info("Update data rejected: not private chat")
        return
    if message.from_user.id != config.ADMIN_ID:
        return

    text = _extract_command_payload(message)
    if not text:
        await message.answer("❗ Укажи сообщение для рассылки.\nПример:\n<code>/sendglobalmessage Привет всем!</code>",
                             parse_mode="HTML")
        return

    chats = await ChatRepository.get_all_chats(session)
    if not chats:
        await message.answer("❗ Нет чатов для рассылки.")
        return

    success, failed = await _send_announcement_to_chats(message, session, text, parse_mode="HTML")

    await message.answer(f"✅ Рассылка завершена.\nУспешно: {success}\nОшибок: {failed}")
