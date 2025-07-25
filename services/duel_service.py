import asyncio
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from database.CRUD.duel_crud import DuelCRUD
from database.models import DuelStatus
from logger import setup_logger

logger = setup_logger(__name__)

async def wait_for_acceptance(bot: Bot, session: AsyncSession, duel_id: int, chat_id: int):
    await asyncio.sleep(300)  # Ждём 5 минут
    duel = await DuelCRUD.get_duel_by_id(session, duel_id)
    if not duel:
        return
    if duel.status == DuelStatus.WAITING_FOR_CONFIRMATION:
        await DuelCRUD.cancel_duel_with_refund(session, duel)
        await session.commit()
        logger.info(f"Duel {duel.id} in chat {chat_id} was automatically cancelled after timeout (no confirmation)")
        await bot.send_message(chat_id, f"⏳ Дуэль была отменена — оппонент не подтвердил вызов в течение 5 минут.")
