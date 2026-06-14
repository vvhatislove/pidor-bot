import asyncio
from aiogram import Bot
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from database.repositories.duel_repository import DuelRepository
from database.models import DuelStatus
from logger import setup_logger

logger = setup_logger(__name__)

async def wait_for_acceptance(
        bot: Bot,
        session_factory: async_sessionmaker[AsyncSession],
        duel_id: int,
        chat_id: int,
) -> None:
    await asyncio.sleep(300)  # Ждём 5 минут
    async with session_factory() as session:
        duel = await DuelRepository.get_duel_by_id(session, duel_id)
        if not duel:
            return
        if duel.status == DuelStatus.WAITING_FOR_CONFIRMATION:
            await DuelRepository.cancel_duel_with_refund(session, duel)
            logger.info(f"Duel {duel.id} in chat {chat_id} was automatically cancelled after timeout (no confirmation)")
            await bot.send_message(chat_id, f"⏳ Дуэль была отменена — оппонент не подтвердил вызов в течение 5 минут.")
