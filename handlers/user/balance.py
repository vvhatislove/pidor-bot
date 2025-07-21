from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import CommandText
from database.crud import UserCRUD
from logger import setup_logger

router = Router()
logger = setup_logger(__name__)


@router.message(Command("balance"))
async def balance_handler(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        logger.info("Rejected /balance: private chat")
        await message.answer(CommandText.WRONG_CHAT)
        return
    user = await UserCRUD.get_user_by_telegram_id(session, message.from_user.id, message.chat.id)
    if user is None:
        await message.reply("Вы ещё не зарегистрированы в этом чате.")
        return

    await message.reply(f"💰 Ваш баланс: {user.balance:.2f} 🪙PidorCoins.")
