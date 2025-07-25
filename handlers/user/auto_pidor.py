# handlers/user/auto_pidor.py

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import CommandText
from database.CRUD.chat_crud import ChatCRUD
from logger import setup_logger

router = Router()
logger = setup_logger(__name__)


@router.message(Command("auto_pidor"))
async def cmd_auto_pidor(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return

    chat_id = message.chat.id
    chat = await ChatCRUD.get_chat(session, chat_id)

    if not chat:
        chat = await ChatCRUD.create_chat(session, chat_id, message.chat.title)

    chat.auto_pidor = not chat.auto_pidor
    await session.commit()
    await message.answer(str(await ChatCRUD.get_auto_pidor_chats(session)))

    status = "✅ Автоматическое определение пидора дня активно В 12:00 каждый день!" if chat.auto_pidor else "❌ Автоматическое определение пидора дня деактивировано"
    logger.info(f"Auto-pidor toggled to {chat.auto_pidor} in chat {chat_id}")
    await message.answer(status)
