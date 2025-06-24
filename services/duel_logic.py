import asyncio
from random import choice

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import DuelCRUD
from database.models import DuelStatus, User, Chat


async def wait_for_acceptance(bot: Bot, session: AsyncSession, duel_id: int, chat_id: int):
    await asyncio.sleep(20)  # Ждём 5 минут

    # Получаем дуэль из БД
    duel = await DuelCRUD.get_duel_by_id(session, duel_id)

    if not duel:
        return  # Дуэль удалена или не найдена

    if duel.status == DuelStatus.WAITING_FOR_CONFIRMATION:
        # Не принята — отменяем
        duel.status = DuelStatus.CANCELLED
        await session.commit()

        # Возврат ставок (если есть)
        # await refund_bets(session, duel)

        # Уведомление
        await bot.send_message(chat_id, f"⏳ Дуэль была отменена — оппонент не подтвердил вызов в течение 5 минут.")



async def schedule_duel_resolution(bot: Bot, session: AsyncSession, duel_id: int):
    # await asyncio.sleep(300)  # 5 минут ожидания

    # Получаем актуальную информацию о дуэли
    duel = await DuelCRUD.get_duel_by_id(session, duel_id)
    if not duel or duel.status != DuelStatus.ACTIVE:
        return  # Дуэль уже завершена или удалена

    # Получаем игроков
    initiator: User = duel.initiator
    opponent:User = duel.opponent

    # Ставки зрителей
    # audience_bets = await session.execute(
    #     select(DuelBet).where(DuelBet.duel_id == duel_id)
    # )
    # audience_bets = audience_bets.scalars().all()

    # Выбираем победителя случайно
    winner_id = choice([initiator.id, opponent.id])
    loser_id = duel.opponent_id if winner_id == duel.initiator_id else duel.initiator_id

    # Расчет коэффициентов и выплат
    payout_messages = []  # соберем список сообщений

    # Обработка логики выплаты
    # ...
    # (вставляется твоя функция payout_winners)

    # # Обновление дуэли
    duel.status = DuelStatus.FINISHED
    duel.winner_id = winner_id
    await session.commit()

    chat: Chat = duel.chat
    telegram_chat_id = chat.telegram_chat_id

    winner_name = initiator.username if winner_id == duel.initiator_id else opponent.username
    message = f"⚔ Дуэль завершена!\nПобедил: <b>{winner_name}</b>\n"
    message += "\n".join(payout_messages) if payout_messages else "\nБез ставок со стороны зрителей."

    await bot.send_message(telegram_chat_id, message, parse_mode="HTML")