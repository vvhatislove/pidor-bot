import asyncio
from random import choice

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import DuelCRUD, CurrencyTransactionCRUD
from database.models import DuelStatus, User, Chat


async def wait_for_acceptance(bot: Bot, session: AsyncSession, duel_id: int, chat_id: int):
    await asyncio.sleep(300)  # Ждём 5 минут

    # Получаем дуэль из БД
    duel = await DuelCRUD.get_duel_by_id(session, duel_id)

    if not duel:
        return  # Дуэль удалена или не найдена

    if duel.status == DuelStatus.WAITING_FOR_CONFIRMATION:
        # Не принята — отменяем
        await DuelCRUD.cancel_duel_with_refund(session, duel)

        # Уведомление
        await bot.send_message(chat_id, f"⏳ Дуэль была отменена — оппонент не подтвердил вызов в течение 5 минут.")



async def schedule_duel_resolution(bot: Bot, session: AsyncSession, duel_id: int):
    await asyncio.sleep(300)  # 5 минут ожидания

    # Получаем актуальную информацию о дуэли
    duel = await DuelCRUD.get_duel_by_id(session, duel_id)
    if not duel or duel.status != DuelStatus.ACTIVE:
        return  # Дуэль уже завершена или удалена

    # Получаем игроков
    initiator: User = duel.initiator
    opponent: User = duel.opponent
    # Выбираем победителя случайно
    winner = choice([initiator, opponent])
    commission = 0.05  # Комиссия 5% от выйгрыша
    winner_payout = round(duel.amount * (1 - commission) + duel.amount, 2)
    # Расчет коэффициентов и выплат
    winner.balance += winner_payout
    await CurrencyTransactionCRUD.create_transaction(session, winner.id, winner_payout, "duel winner payout")
    duel.status = DuelStatus.FINISHED
    duel.winner_id = winner.id
    await session.commit()

    chat: Chat = duel.chat
    telegram_chat_id = chat.telegram_chat_id

    winner_name = initiator.username if winner == duel.initiator else opponent.username
    message = f"⚔ Дуэль завершена!\nПобедил: <b>{winner_name}</b>\n"
    message += f"Победитель получает: <b>{winner_payout} PidorCoins</b>. Комиссия {commission*100}% от выйгрыша\n"

    await bot.send_message(telegram_chat_id, message, parse_mode="HTML")