import asyncio
from random import choice

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import DuelCRUD, CurrencyTransactionCRUD
from database.models import DuelStatus
from logger import setup_logger

logger = setup_logger(__name__)

async def wait_for_acceptance(bot: Bot, session: AsyncSession, duel_id: int, chat_id: int):
    await asyncio.sleep(300)  # Ждём 5 минут

    # Получаем дуэль из БД
    duel = await DuelCRUD.get_duel_by_id(session, duel_id)

    if not duel:
        return  # Дуэль удалена или не найдена

    if duel.status == DuelStatus.WAITING_FOR_CONFIRMATION:
        # Не принята — отменяем
        await DuelCRUD.cancel_duel_with_refund(session, duel)
        await session.commit()

        logger.info(f"Duel {duel.id} in chat {chat_id} was automatically cancelled after timeout (no confirmation)")

        # Уведомление
        await bot.send_message(chat_id, f"⏳ Дуэль была отменена — оппонент не подтвердил вызов в течение 5 минут.")
