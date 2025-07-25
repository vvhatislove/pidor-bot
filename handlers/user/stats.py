from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from database.CRUD.user_crud import UserCRUD
from config.constants import CommandText
from logger import setup_logger

router = Router()
logger = setup_logger(__name__)

@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    logger.info(f"/stats requested by user {message.from_user.id} in chat {message.chat.id}")

    if message.chat.type == "private":
        logger.info("Rejected /stats: private chat")
        await message.answer(CommandText.WRONG_CHAT)
        return

    users = await UserCRUD.get_chat_users(session, message.chat.id)
    if not users:
        logger.info(f"No users found for stats in chat {message.chat.id}")
        await message.answer("Нет зарегистрированных участников 😔")
        return

    users.sort(key=lambda x: x.pidor_count, reverse=True)
    logger.info(f"Sorted {len(users)} users for stats display")

    medals = ['🥇', '🥈', '🥉']
    stats_message_text = f'Статистика пидорасов чата "{message.chat.title}" 👇\n'

    for i, user in enumerate(users):
        username = user.username.strip() if user.username and user.username.strip().lower() != 'none' else user.first_name.strip()
        count = user.pidor_count
        medal = medals[i] if i < len(medals) else '💩'
        stats_message_text += f"👨‍❤️‍💋‍👨 {username} — {count} раз(а) {medal}\n"

    await message.answer(stats_message_text)