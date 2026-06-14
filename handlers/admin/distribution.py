from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import config
from database.repositories.chat_repository import ChatRepository
from database.repositories.user_repository import UserRepository
from logger import setup_logger

logger = setup_logger(__name__)

router = Router()


@router.message(Command("send_global_message", "sendglobalmessage"))
async def cmd_send_global_message(message: Message, session: AsyncSession):
    if message.chat.type != "private":
        logger.info("Update data rejected: not private chat")
        return
    user = await UserRepository.get_user_by_telegram_id(session, message.from_user.id,
                                                  message.chat.id)  # не работает, пока костыльно буду получать из константы
    if not user:
        if message.from_user.id != config.ADMIN_ID:
            return
    elif not user.is_admin:
        return

    parts = (message.text or "").split(maxsplit=1)
    text = parts[1].strip() if len(parts) > 1 else ""
    if not text:
        await message.answer("❗ Укажи сообщение для рассылки.\nПример:\n<code>/sendglobalmessage Привет всем!</code>",
                             parse_mode="HTML")
        return

    chats = await ChatRepository.get_all_chats(session)
    if not chats:
        await message.answer("❗ Нет чатов для рассылки.")
        return

    success, failed = 0, 0
    for chat in chats:
        try:
            await message.bot.send_message(chat.telegram_chat_id, text, parse_mode="HTML")
            success += 1
        except Exception as e:
            logger.warning(f"Failed to send message to chat {chat.telegram_chat_id}: {e}")
            failed += 1

    await message.answer(f"✅ Рассылка завершена.\nУспешно: {success}\nОшибок: {failed}")
