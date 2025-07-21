import asyncio
import random

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import GameText, CommandText, AIPromt, Cooldown
from database.crud import UserCRUD, CurrencyTransactionCRUD
from handlers.utils import get_display_name
from logger import setup_logger
from services.ai_service import AIService
from services.cooldown import CooldownService

router = Router()
logger = setup_logger(__name__)


@router.message(Command("pidor"))
async def cmd_pidor(message: Message, session: AsyncSession):
    logger.info(f"/pidor invoked by user {message.from_user.id} in chat {message.chat.id}")

    if message.chat.type == "private":
        logger.info("Rejected /pidor: private chat")
        await message.answer(CommandText.WRONG_CHAT)
        return

    if await CooldownService.check_cooldown(session, message.chat.id):
        logger.info(f"Cooldown active in chat {message.chat.id}")
        await message.answer("🐔Пидор на сегодня уже известен. ♻️Попробуйте завтра")
        return

    users = await UserCRUD.get_chat_users(session, message.chat.id)
    if not users:
        logger.info(f"No registered users in chat {message.chat.id}")
        await message.answer("Нет зарегистрированных участников 😔")
        return

    logger.info(f"Starting pidor selection among {len(users)} users")
    await message.answer("Так так так... Погодите-ка...🔍")

    search_phrases = await AIService.get_response("", AIPromt.SERCHING_PIDOR_PROMPT)
    search_phrases = search_phrases.split("|")
    if not len(search_phrases):
        search_phrases.extend(random.sample(GameText.SEARCH_PHRASES, min(2, len(GameText.SEARCH_PHRASES))))
        search_phrases = list(set(search_phrases))[:2]
    win_phrase = await AIService.get_response("", AIPromt.WIN_PHRASE_PIDOR_PROMPT)
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
    await CurrencyTransactionCRUD.create_transaction(session, pidor.id, pidor_coins, "pidor of the day")
    logger.info(f"Created pidor of the day transaction for user {pidor.telegram_id}")
    await session.commit()
    logger.info(f"Updated pidor count for user {pidor.telegram_id}: {pidor.pidor_count}")
    logger.info(f"Increased balance for user {pidor.telegram_id}: {pidor_coins}")

    await CooldownService.activate_cooldown(session, message.chat.id, Cooldown.DEFAULT)  # Cooldown.DEFAULT
    logger.info(f"Cooldown activated for chat {message.chat.id}")

    await message.answer(win_phrase + f"\n\n\n+🪙{pidor_coins} PidorCoins нашему пидорасику")

    if pidor.pidor_count in GameText.ACHIEVEMENTS:
        achievement = GameText.ACHIEVEMENTS[pidor.pidor_count]
        await message.answer(
            f"🎉 {pidor.first_name if pidor.first_name else pidor.username} открыл достижение:\n"
            f"{achievement[0]}\n{achievement[1]}"
        )
        logger.info(f"User {pidor.telegram_id} unlocked achievement: {achievement[0]}")
