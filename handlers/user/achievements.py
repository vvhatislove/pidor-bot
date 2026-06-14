from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import GameText, CommandText
from database.repositories.user_repository import UserRepository
from handlers.formatting import get_display_name
from logger import setup_logger

router = Router()
logger = setup_logger(__name__)


@router.message(Command("achievements"))
async def cmd_achievements(message: Message, session: AsyncSession):
    logger.info(f"/achievements requested by user {message.from_user.id} in chat {message.chat.id}")

    if message.chat.type == "private":
        logger.info("Rejected /achievements: private chat")
        await message.answer(CommandText.WRONG_CHAT)
        return

    user = await UserRepository.get_user_by_telegram_id(session, message.from_user.id, message.chat.id)
    if not user:
        logger.info(f"User {message.from_user.id} not registered in chat {message.chat.id}")
        await message.answer("Вы не зарегистрированы в чате")
        return

    achievement_lines = [f"🎖 Достижения {get_display_name(user)}:\n"]
    for threshold, (title, description) in sorted(GameText.ACHIEVEMENTS.items()):
        achieved = user.pidor_count >= threshold
        status = "✅ Получено" if achieved else "🔒 Не получено"
        description = description.replace("✅", "")
        achievement_lines.append(f"{title}\n↪️ {description}\n{status}\n")

    logger.info(f"Displayed achievements for user {user.telegram_id} with {user.pidor_count} count")
    await message.answer("\n".join(achievement_lines))
