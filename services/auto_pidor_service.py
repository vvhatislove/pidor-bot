import asyncio

from aiogram import Bot
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from database import async_session
from database.repositories.chat_repository import ChatRepository
from services.pidor_service import run_pidor_selection
from logger import setup_logger
from services.scheduling_service import wait_until

logger = setup_logger(__name__)

AUTO_PIDOR_CONCURRENCY = 5


async def auto_pidor_scheduler(bot: Bot):
    logger.info("Auto Pidor Scheduler started")
    while True:
        try:
            await wait_until(12, 00)
            logger.info("Running auto-pidor routine")
            await run_pidor_for_all(bot, async_session)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Auto-pidor scheduler iteration failed")
            await asyncio.sleep(60)


async def run_pidor_for_all(bot: Bot, session_factory: async_sessionmaker[AsyncSession]):
    async with session_factory() as session:
        chats = await ChatRepository.get_auto_pidor_chats(session)
        chat_ids = [chat.telegram_chat_id for chat in chats]
    logger.info(f"Found {len(chat_ids)} chats with auto_pidor enabled")

    semaphore = asyncio.Semaphore(AUTO_PIDOR_CONCURRENCY)

    async def run_for_chat(chat_id: int) -> None:
        async with semaphore:
            try:
                logger.info(f"Launching auto-pidor in chat {chat_id}")
                async with session_factory() as session:
                    await run_pidor_selection(
                        chat_id=chat_id,
                        send_func=bot.send_message,
                        session=session,
                        is_automatic=True
                    )
            except Exception:
                logger.exception(f"Failed to run auto-pidor in chat {chat_id}")

    await asyncio.gather(*(run_for_chat(chat_id) for chat_id in chat_ids))
