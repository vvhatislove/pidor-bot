from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import CommandText
from database.models import Achievement
from database.repositories.user_repository import UserRepository
from handlers.formatting import get_display_name
from logger import setup_logger
from services.achievement_service import AchievementService

router = Router()
logger = setup_logger(__name__)


@router.message(Command("achievements"))
async def cmd_achievements(message: Message, session: AsyncSession):
    logger.info(f"/achievements requested by user {message.from_user.id} in chat {message.chat.id}")

    if message.chat.type == "private":
        logger.info("Rejected /achievements: private chat")
        await message.answer(CommandText.WRONG_CHAT)
        return

    user = await UserRepository.get_user_by_telegram_id(session, message.from_user.id, message.chat.id)
    if not user:
        logger.info(f"User {message.from_user.id} not registered in chat {message.chat.id}")
        await message.answer("Вы не зарегистрированы в чате")
        return

    await AchievementService.ensure_catalog(session)
    await session.commit()

    result = await session.execute(
        select(Achievement)
        .where(Achievement.is_active.is_(True))
        .order_by(Achievement.category, Achievement.target_value, Achievement.id)
    )
    achievements = list(result.scalars().all())
    unlocked_codes = await AchievementService.get_user_achievement_codes(session, user.id)

    unlocked_count = len([achievement for achievement in achievements if achievement.code in unlocked_codes])
    total_reward = sum(achievement.reward_amount for achievement in achievements if achievement.code in unlocked_codes)
    achievement_lines = [
        f"🎖 <b>Достижения {get_display_name(user)}</b>",
        f"Получено: <b>{unlocked_count}/{len(achievements)}</b>",
        f"Наград получено: <b>{total_reward:.2f}</b> 🪙\n",
    ]

    current_category = None
    for achievement in achievements:
        if achievement.category != current_category:
            current_category = achievement.category
            achievement_lines.append(f"\n<b>{_category_title(current_category)}</b>")

        unlocked = achievement.code in unlocked_codes
        status = "✅" if unlocked else "🔒"
        progress = achievement.target_value if unlocked else await AchievementService.achievement_progress(session, user, achievement)
        achievement_lines.append(
            f"{status} {achievement.title} — {progress}/{achievement.target_value} | +{achievement.reward_amount:.2f} 🪙\n"
            f"↪️ {achievement.description}"
        )

    logger.info(f"Displayed achievements for user {user.telegram_id}: {unlocked_count}/{len(achievements)}")
    await message.answer("\n".join(achievement_lines), parse_mode="HTML")


def _category_title(category: str) -> str:
    return {
        "activity": "Активность",
        "balance": "Баланс",
        "duels": "Дуэли",
        "pidor": "Пидор дня",
        "slots": "Слоты",
    }.get(category, category)
