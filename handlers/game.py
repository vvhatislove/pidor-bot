import asyncio

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from database.crud import UserCRUD
from services.cooldown import CooldownService
from config.constants import GameText, CommandText
import random
import time

router = Router()


@router.message(Command("pidor"))
async def pidor_game(message: Message, session: AsyncSession):
    # Проверка типа чата
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return

    # Проверка кулдауна
    cooldown_status = await CooldownService.check_cooldown(session, message.chat.id)
    if cooldown_status:
        await message.answer(
            f"До следующего определения пидора осталось {cooldown_status} ⏳"
        )
        return

    # Получаем участников
    users = await UserCRUD.get_chat_users(session, message.chat.id)
    if not users:
        await message.answer("Нет зарегистрированных участников 😔")
        return

    # Анимация поиска
    search_phrase = random.choice(GameText.SEARCH_PHRASES)
    await message.answer(search_phrase)
    await asyncio.sleep(1.5)

    # Выбор пидора дня
    pidor = random.choice(users)
    win_phrase = random.choice(GameText.WIN_PHRASES).format(
        winner=pidor.username or pidor.first_name
    )

    # Обновляем статистику
    pidor.pidor_count += 1
    await session.commit()

    # Активируем кулдаун
    await CooldownService.activate_cooldown(session, message.chat.id)

    # Отправляем результат
    await message.answer(win_phrase)

    if pidor.pidor_count in GameText.ACHIEVEMENTS:
        await message.answer(
            f"🎉 {pidor.first_name if pidor.first_name else pidor.username} открыл достижение:\n"
            f"{GameText.ACHIEVEMENTS[pidor.pidor_count][0]}\n"
            f"{GameText.ACHIEVEMENTS[pidor.pidor_count][1]}"
        )