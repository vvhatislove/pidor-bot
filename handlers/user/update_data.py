from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import CommandText
from database.CRUD.user_crud import UserCRUD
from logger import setup_logger

logger = setup_logger(__name__)

router = Router()


@router.message(Command("update_data"))
async def cmd_update_data(message: Message, session: AsyncSession):
    logger.info(f"/update_data called by user {message.from_user.id} in chat {message.chat.id}")

    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        logger.info("Update data rejected: private chat")
        return

    user = await UserCRUD.get_user_by_telegram_id(session, message.from_user.id, message.chat.id)
    if not user:
        await message.answer("Вы не зарегистрированы в чате")
        logger.info("User not found for update")
        return

    await UserCRUD.update_user_and_chat(
        session,
        message.from_user.id,
        message.chat.id,
        message.from_user.first_name,
        message.from_user.username,
        message.chat.title
    )
    logger.info(f"User {message.from_user.id} updated in chat {message.chat.id}")
    await message.answer(
        f"Твои данные перезаписаны в ПидорБазу!📃\n👉Имя: {message.from_user.first_name}\n👉Никнейм: {message.from_user.username}"
    )
