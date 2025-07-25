import asyncio
import random
from typing import Callable, Awaitable, Any

from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import GameText, AIPromt
from database.CRUD.currency_transaction_crud import CurrencyTransactionCRUD
from database.CRUD.user_crud import UserCRUD
from handlers.utils.utils import get_display_name
from logger import setup_logger
from handlers.utils.AI import AI
from handlers.utils.cooldown_logic import Cooldown

logger = setup_logger(__name__)


async def run_pidor_selection(
        chat_id: int,
        send_func: Callable[..., Awaitable[Any]],  # message.answer или bot.send_message(chat_id, ...)
        session: AsyncSession,
        is_automatic: bool
):
    if await Cooldown.check_cooldown(session, chat_id):
        logger.info(f"Cooldown active in chat {chat_id}")
        if is_automatic:
            return
        await send_func(chat_id, "🐔Пидор на сегодня уже известен. ♻️Попробуйте завтра")
        return

    users = await UserCRUD.get_chat_users(session, chat_id)
    if not users:
        logger.info(f"No registered users in chat {chat_id}")
        await send_func(chat_id, "Нет зарегистрированных участников 😔")
        return

    logger.info(f"Starting pidor selection among {len(users)} users")
    if is_automatic:
        await send_func(chat_id, "Автоматический выбор пидора дня... 🤖")
    else:
        await send_func(chat_id, "Так так так... Погодите-ка...🔍")
    search_phrases = await AI.get_response("", AIPromt.SERCHING_PIDOR_PROMPT)
    search_phrases = search_phrases.split("|")
    if not search_phrases or len(search_phrases) < 2:
        search_phrases.extend(random.sample(GameText.SEARCH_PHRASES, min(2, len(GameText.SEARCH_PHRASES))))
        search_phrases = list(set(search_phrases))[:2]

    win_phrase = await AI.get_response("", AIPromt.WIN_PHRASE_PIDOR_PROMPT)
    if not win_phrase:
        win_phrase = random.choice(GameText.WIN_PHRASES)

    await send_func(chat_id, search_phrases[0])
    await asyncio.sleep(1.5)
    await send_func(chat_id, search_phrases[1])
    await asyncio.sleep(1.5)

    pidor = random.choice(users)
    win_phrase = win_phrase.format(name=get_display_name(pidor))

    logger.info(f"Selected pidor of the day: {pidor.telegram_id}")
    pidor.pidor_count += 1
    reward = 100
    await UserCRUD.increase_balance(session, pidor.telegram_id, reward)
    await CurrencyTransactionCRUD.create_transaction(session, pidor.id, reward, "pidor of the day")
    await session.commit()
    logger.info(f"Awarded {reward} coins to user {pidor.telegram_id}")

    await Cooldown.activate_cooldown(session, chat_id)
    await send_func(chat_id, win_phrase + f"\n\n\n+🪙{reward} PidorCoins нашему пидорасику")

    if pidor.pidor_count in GameText.ACHIEVEMENTS:
        achievement = GameText.ACHIEVEMENTS[pidor.pidor_count]
        await send_func(chat_id,
                        f"🎉 {pidor.first_name or pidor.username} открыл достижение:\n"
                        f"{achievement[0]}\n{achievement[1]}"
                        )
        logger.info(f"User {pidor.telegram_id} unlocked achievement: {achievement[0]}")
