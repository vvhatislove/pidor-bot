import asyncio
import re
from datetime import datetime, UTC

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from database.crud import UserCRUD, CurrencyTransactionCRUD, DuelCRUD, ChatCRUD
from database.models import DuelStatus
from handlers.utils import get_display_name
from services.ai_service import AIService
from services.cooldown import CooldownService
from config.constants import GameText, CommandText, AIPromt, Cooldown
import random
from logger import setup_logger
from services.duel_logic import wait_for_acceptance, schedule_duel_resolution
from services.slots_logic import get_combo_text

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

@router.message(Command("duel"))
async def cmd_duel(message: Message, session: AsyncSession):
    # Проверка, что это группа
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return

    # Извлекаем username и сумму
    pattern = r"/duel\s+@(\w+)\s+(\d+(?:[.,]\d{1,2})?)"
    match = re.match(pattern, message.text.strip())

    if not match:
        await message.answer("Неверный формат. Используйте: /duel @username 100")
        return
    username_opponent = match.group(1)
    amount = float(match.group(2))
    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.")
        return
    if username_opponent == message.from_user.username:
        await message.answer("Нельзя драться самому с собой")
        return
    initiator = await UserCRUD.get_user_by_username(session, message.from_user.username, message.chat.id)
    if not initiator:
        await message.answer("Вы не зарегистрированы в чате")
        return
    opponent = await UserCRUD.get_user_by_username(session, username_opponent, message.chat.id)
    if not opponent:
        await message.answer(f"Пользователь {username_opponent} не зарегистрирован в базе")
        return
    if initiator.balance < amount:
        await message.answer("Недостаточно средств")
        return
    if opponent.balance < amount:
        await message.answer(f"У пользователя {username_opponent} недостаточно средств")
        return
    chat = await ChatCRUD.get_chat(session, message.chat.id)
    initiator.balance -= amount
    opponent.balance -= amount
    await CurrencyTransactionCRUD.create_transaction(session, initiator.telegram_id, amount, "duel initiator bet")
    await CurrencyTransactionCRUD.create_transaction(session, opponent.telegram_id, amount, "duel opponent bet")
    duel = await DuelCRUD.create_duel(session, chat.id, initiator.id, opponent.id, amount)
    await session.commit()
    await message.answer(f"@{message.from_user.username} по пидорски вызвал на дуэль @{username_opponent} на сумму {amount} PidorCoins")
    asyncio.create_task(wait_for_acceptance(message.bot, session, duel.id, message.chat.id))

@router.message(Command("accept_duel"))
async def cmd_accept_duel(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return
    duel = await DuelCRUD.get_pending_confirmation(session, message.chat.id, message.from_user.id)
    if not duel:
        await message.answer("Вас не вызывали на дуэль")
        return
    duel.status = DuelStatus.ACTIVE
    duel.accepted_at = datetime.now(UTC)
    await session.commit()
    await message.answer("Дуэль принята, начало через 5мин, начат прием ставок")
    asyncio.create_task(schedule_duel_resolution(message.bot, session, duel.id))

@router.message(Command("test"))
async def cmd_test(message: Message, session: AsyncSession):
    bot = message.bot
    data = await bot.send_dice(message.chat.id, emoji='🎰')
    await bot.send_message(message.chat.id, f'значение слоты {get_combo_text(data.dice.value)}')
