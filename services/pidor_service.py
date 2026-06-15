import asyncio
import random
from typing import Callable, Awaitable, Any

from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import GameText, AIPrompt
from database.repositories.currency_transaction_repository import CurrencyTransactionRepository
from database.repositories.user_repository import UserRepository
from database.transaction_reasons import TransactionReason
from handlers.formatting import get_display_name
from logger import setup_logger
from services.achievement_service import AchievementService
from services.ai_response_buffer import ai_response_buffer
from services.ai_service import AIService
from services.cooldown_service import CooldownService

logger = setup_logger(__name__)

PIDOR_REWARD = 100


def _search_phrases_from_ai_response(response: str) -> list[str]:
    phrases = [phrase.strip() for phrase in response.split("|") if phrase.strip()]
    if len(phrases) >= 2:
        return phrases[:2]
    fallback = random.sample(GameText.SEARCH_PHRASES, min(2, len(GameText.SEARCH_PHRASES)))
    return (phrases + fallback)[:2]


def _format_win_phrase(template: str, display_name: str) -> str:
    if not template:
        template = random.choice(GameText.WIN_PHRASES)
    try:
        phrase = template.format(name=display_name)
    except (IndexError, KeyError, ValueError):
        logger.warning("Invalid pidor win phrase template from AI: %r", template)
        phrase = random.choice(GameText.WIN_PHRASES).format(name=display_name)
    if display_name not in phrase:
        phrase = f"{phrase} {display_name}"
    return phrase


async def run_pidor_selection(
        chat_id: int,
        send_func: Callable[..., Awaitable[Any]],  # message.answer или bot.send_message(chat_id, ...)
        session: AsyncSession,
        is_automatic: bool
):
    if await CooldownService.check_cooldown(session, chat_id):
        logger.info(f"Cooldown active in chat {chat_id}")
        if is_automatic:
            return
        today_pidor = await CooldownService.get_today_pidor(session, chat_id)
        if today_pidor:
            await send_func(
                chat_id,
                f"🐔Пидор на сегодня уже известен: {get_display_name(today_pidor)}\n"
                "♻️Попробуйте завтра"
            )
        else:
            await send_func(chat_id, "🐔Пидор на сегодня уже известен. ♻️Попробуйте завтра")
        return

    users = await UserRepository.get_chat_users(session, chat_id)
    if not users:
        logger.info(f"No active pidor participants in chat {chat_id}")
        await send_func(chat_id, "Нет активных участников розыгрыша пидора дня 😔")
        return

    logger.info(f"Starting pidor selection among {len(users)} users")
    if is_automatic:
        await send_func(chat_id, "Автоматический выбор пидора дня... 🤖")
    else:
        await send_func(chat_id, "Так так так... Погодите-ка...🔍")
    search_response = await ai_response_buffer.pop("pidor_searching")
    if not search_response:
        search_response = await AIService.get_response("", AIPrompt.SEARCHING_PIDOR_PROMPT)
    search_phrases = _search_phrases_from_ai_response(search_response)

    win_phrase = await ai_response_buffer.pop("pidor_win_phrase")
    if not win_phrase:
        win_phrase = await AIService.get_response("", AIPrompt.WIN_PHRASE_PIDOR_PROMPT)

    await send_func(chat_id, search_phrases[0])
    await asyncio.sleep(1.5)
    await send_func(chat_id, search_phrases[1])
    await asyncio.sleep(1.5)

    pidor = random.choice(users)
    win_phrase = _format_win_phrase(win_phrase, get_display_name(pidor))

    logger.info(f"Selected pidor of the day: {pidor.telegram_id}")
    pidor.pidor_count += 1
    reward = PIDOR_REWARD
    await UserRepository.increase_balance(session, pidor.id, reward)
    await CurrencyTransactionRepository.create_transaction(session, pidor.id, reward, TransactionReason.PIDOR_REWARD)
    achievements = await AchievementService.check_pidor(session, pidor)
    await session.commit()
    logger.info(f"Awarded {reward} coins to user {pidor.telegram_id}")

    await CooldownService.activate_cooldown(session, chat_id, pidor_user_id=pidor.id)
    await send_func(chat_id, win_phrase + f"\n\n\n+🪙{reward} PidorCoins нашему пидорасику")
    await AchievementService.notify(lambda text: send_func(chat_id, text, parse_mode="HTML"), pidor, achievements)
