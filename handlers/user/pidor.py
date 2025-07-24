from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import CommandText
from handlers.utils.pidor_logic import run_pidor_selection
from logger import setup_logger

logger = setup_logger(__name__)
router = Router()


@router.message(Command("pidor"))
async def cmd_pidor(message: Message, session: AsyncSession):
    logger.info(f"/pidor invoked by user {message.from_user.id} in chat {message.chat.id}")

    if message.chat.type == "private":
        logger.info("Rejected /pidor: private chat")
        await message.answer(CommandText.WRONG_CHAT)
        return

    await run_pidor_selection(message.chat.id, message.bot.send_message, session, is_automatic=False)
