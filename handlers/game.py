import asyncio

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from database.crud import UserCRUD, CurrencyTransactionCRUD
from handlers.utils import get_display_name
from services.ai_service import AIService
from services.cooldown import CooldownService
from config.constants import GameText, CommandText, AIPromt, Cooldown
import random
from logger import setup_logger

logger = setup_logger(__name__)

router = Router()


@router.message(Command("pidor"))
async def cmd_pidor(message: Message, session: AsyncSession):
    logger.info(f"/pidor invoked by user {message.from_user.id} in chat {message.chat.id}")

    if message.chat.type == "private":
        logger.info("Rejected /pidor: private chat")
        await message.answer(CommandText.WRONG_CHAT)
        return

    if await CooldownService.check_cooldown(session, message.chat.id):
        logger.info(f"Cooldown active in chat {message.chat.id}")
        await message.answer("🐔Пидор на сегодня уже известен. ♻️Попробуйте завтра")
        return

    users = await UserCRUD.get_chat_users(session, message.chat.id)
    if not users:
        logger.info(f"No registered users in chat {message.chat.id}")
        await message.answer("Нет зарегистрированных участников 😔")
        return

    logger.info(f"Starting pidor selection among {len(users)} users")
    await message.answer("Так так так... Погодите-ка...🔍")

    search_phrases = await AIService.get_response("", AIPromt.SERCHING_PIDOR_PROMT)
    search_phrases = search_phrases.split("|")
    if not len(search_phrases):
        search_phrases.extend(random.sample(GameText.SEARCH_PHRASES, min(2, len(GameText.SEARCH_PHRASES))))
        search_phrases = list(set(search_phrases))[:2]
    win_phrase = await AIService.get_response("", AIPromt.WIN_PHRASE_PIDOR_PROMT)
    if not win_phrase:
        win_phrase = random.choice(GameText.WIN_PHRASES)

    await message.answer(search_phrases[0])
    await asyncio.sleep(1.5)
    await message.answer(search_phrases[1])
    await asyncio.sleep(1.5)

    pidor = random.choice(users)
    win_phrase = win_phrase.format(
        name=get_display_name(pidor)
    )
    logger.info(f"Selected pidor of the day: {pidor.telegram_id}")
    pidor.pidor_count += 1
    pidor_coins = 100
    await  UserCRUD.increase_balance(session, pidor.telegram_id, pidor_coins)
    await CurrencyTransactionCRUD.create_transaction(session, pidor.telegram_id, pidor_coins, "pidor of the day")
    logger.info(f"Created pidor of the day transaction for user {pidor.telegram_id}")
    await session.commit()
    logger.info(f"Updated pidor count for user {pidor.telegram_id}: {pidor.pidor_count}")
    logger.info(f"Increased balance for user {pidor.telegram_id}: {pidor_coins}")

    await CooldownService.activate_cooldown(session, message.chat.id, Cooldown.DEFAULT) # Cooldown.DEFAULT
    logger.info(f"Cooldown activated for chat {message.chat.id}")

    await message.answer(win_phrase + f"\n\n\n+🪙{pidor_coins} PidorCoins нашему пидорасику")

    if pidor.pidor_count in GameText.ACHIEVEMENTS:
        achievement = GameText.ACHIEVEMENTS[pidor.pidor_count]
        await message.answer(
            f"🎉 {pidor.first_name if pidor.first_name else pidor.username} открыл достижение:\n"
            f"{achievement[0]}\n{achievement[1]}"
        )
        logger.info(f"User {pidor.telegram_id} unlocked achievement: {achievement[0]}")


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


@router.message(Command("achievements"))
async def cmd_achievements(message: Message, session: AsyncSession):
    logger.info(f"/achievements requested by user {message.from_user.id} in chat {message.chat.id}")

    if message.chat.type == "private":
        logger.info("Rejected /achievements: private chat")
        await message.answer(CommandText.WRONG_CHAT)
        return

    user = await UserCRUD.get_user(session, message.from_user.id, message.chat.id)
    if not user:
        logger.info(f"User {message.from_user.id} not registered in chat {message.chat.id}")
        await message.answer("Вы не зарегистрированы в чате")
        return

    achievement_lines = ["🎖 Достижения:\n"]
    for threshold, (title, description) in sorted(GameText.ACHIEVEMENTS.items()):
        achieved = user.pidor_count >= threshold
        status = "✅ Получено" if achieved else "🔒 Не получено"
        description = description.replace("✅", "")
        achievement_lines.append(f"{title}\n↪️ {description}\n{status}\n")

    logger.info(f"Displayed achievements for user {user.telegram_id} with {user.pidor_count} count")
    await message.answer("\n".join(achievement_lines))