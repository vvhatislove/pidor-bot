import asyncio

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from database.crud import UserCRUD
from services.ai_service import AIService
from services.cooldown import CooldownService
from config.constants import GameText, CommandText, AIPromt, Cooldown
import random

router = Router()


@router.message(Command("pidor"))
async def cmd_pidor(message: Message, session: AsyncSession):
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
    await message.answer("Так так так... Погодите-ка...🔍")

    # Анимация поиска
    search_phrases = await AIService.get_response("", AIPromt.SERCHING_PIDOR_PROMT)
    search_phrases = search_phrases.split("|")
    win_phrase = await AIService.get_response("", AIPromt.WIN_PHRASE_PIDOR_PROMT)
    await message.answer(search_phrases[0])
    await asyncio.sleep(1.5)
    await message.answer(search_phrases[1])
    await asyncio.sleep(1.5)

    # Выбор пидора дня
    pidor = random.choice(users)
    win_phrase = win_phrase.format(
        name=f"@{pidor.username}" if pidor.username else pidor.first_name
    )

    # Обновляем статистику
    pidor.pidor_count += 1
    await session.commit()

    # Активируем кулдаун
    await CooldownService.activate_cooldown(session, message.chat.id, Cooldown.DEFAULT)

    # Отправляем результат
    await message.answer(win_phrase)

    if pidor.pidor_count in GameText.ACHIEVEMENTS:
        await message.answer(
            f"🎉 {pidor.first_name if pidor.first_name else pidor.username} открыл достижение:\n"
            f"{GameText.ACHIEVEMENTS[pidor.pidor_count][0]}\n"
            f"{GameText.ACHIEVEMENTS[pidor.pidor_count][1]}"
        )

@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return

    users = await UserCRUD.get_chat_users(session, message.chat.id)
    if not users:
        await message.answer("Нет зарегистрированных участников 😔")
        return

    medals = ['🥇', '🥈', '🥉']
    stats_message_text = f'Статистика пидорасов чата "{message.chat.title}" 👇\n'

    # Сортировка по полю pidor_count по убыванию
    users.sort(key=lambda x: x.pidor_count, reverse=True)

    for i, user in enumerate(users):
        username = user.username.strip() if user.username and user.username.strip().lower() != 'none' else user.first_name.strip()
        count = user.pidor_count

        medal = medals[i] if i < len(medals) else '💩'
        stats_message_text += f"👨‍❤️‍💋‍👨 {username} — {count} раз(а) {medal}\n"

    await message.answer(stats_message_text)


@router.message(Command("achievements"))
async def cmd_achievements(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return

    user = await UserCRUD.get_user(session, message.from_user.id, message.chat.id)
    if not user:
        await message.answer("Вы не зарегистрированы в чате")
        return

    achievement_lines = ["🎖 Достижения:\n"]

    for threshold, (title, description) in sorted(GameText.ACHIEVEMENTS.items()):
        achieved = user.pidor_count >= threshold
        status = "✅ Получено" if achieved else "🔒 Не получено"
        description = description.replace("✅", "")
        achievement_lines.append(f"{title}\n↪️ {description}\n{status}\n")
    await message.answer("\n".join(achievement_lines))