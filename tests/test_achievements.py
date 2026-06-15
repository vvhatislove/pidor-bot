from types import SimpleNamespace

from sqlalchemy import select

from database.models import Achievement, UserAchievement
from database.repositories.chat_repository import ChatRepository
from database.repositories.currency_transaction_repository import CurrencyTransactionRepository
from database.repositories.user_repository import UserRepository
from handlers.user.achievements import cmd_achievements
from services.achievement_service import ACHIEVEMENTS, AchievementService


class FakeMessage:
    def __init__(self):
        self.chat = SimpleNamespace(id=-100, type="group", title="chat")
        self.from_user = SimpleNamespace(id=1)
        self.answers = []

    async def answer(self, text: str, **kwargs):
        self.answers.append(text)


async def _create_user(session):
    await ChatRepository.create_chat(session, -100, "chat")
    return await UserRepository.create_user(
        session=session,
        telegram_id=1,
        chat_telegram_id=-100,
        first_name="User",
        username="user",
    )


async def test_achievement_catalog_is_seeded(session):
    await AchievementService.ensure_catalog(session)
    await session.commit()

    result = await session.execute(select(Achievement))
    achievements = result.scalars().all()

    assert len(achievements) == len(ACHIEVEMENTS)
    assert {achievement.code for achievement in achievements} >= {"pidor_1", "slots_jackpot_1", "duel_wins_10"}


async def test_unlock_achievement_rewards_once(session):
    user = await _create_user(session)

    first = await AchievementService.unlock(session, user, "pidor_1")
    second = await AchievementService.unlock(session, user, "pidor_1")
    await session.commit()

    assert first is not None
    assert second is None
    assert user.balance == 100

    result = await session.execute(select(UserAchievement))
    assert len(result.scalars().all()) == 1

    transactions = await CurrencyTransactionRepository.get_user_transactions(session, user.id)
    assert [(tx.reason, tx.amount) for tx in transactions] == [("achievement_reward code=pidor_1", 100)]


async def test_achievements_command_shows_catalog_and_progress(session):
    user = await _create_user(session)
    user.pidor_count = 3
    await AchievementService.unlock(session, user, "pidor_1")
    await session.commit()
    message = FakeMessage()

    await cmd_achievements(message, session)

    assert len(message.answers) == 1
    text = message.answers[0]
    assert "Получено:" in text
    assert "✅ 🍍 Первый залет" in text
    assert "🔒 🍩 Тройной петух — 3/3" in text
    assert "+100.00 🪙" in text
