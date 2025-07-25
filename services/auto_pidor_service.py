from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session
from database.CRUD.chat_crud import ChatCRUD
from handlers.utils.pidor_logic import run_pidor_selection
from logger import setup_logger
from services.utils import wait_until

logger = setup_logger(__name__)


async def auto_pidor_scheduler(bot: Bot):
    logger.info("Auto Pidor Scheduler started")
    while True:
        await wait_until(12, 00)
        logger.info("Running auto-pidor routine")
        async with async_session() as session:
            await run_pidor_for_all(bot, session)


async def run_pidor_for_all(bot: Bot, session: AsyncSession):
    chats = await ChatCRUD.get_auto_pidor_chats(session)
    logger.info(f"Found {len(chats)} chats with auto_pidor enabled")

    for chat in chats:
        try:
            logger.info(f"Launching auto-pidor in chat {chat.telegram_chat_id}")
            await run_pidor_selection(
                chat_id=chat.telegram_chat_id,
                send_func=lambda text: bot.send_message(chat.telegram_chat_id, text),
                session=session,
                is_automatic=True
            )
        except Exception as e:
            logger.error(f"Failed to run auto-pidor in chat {chat.telegram_chat_id}: {e}")
