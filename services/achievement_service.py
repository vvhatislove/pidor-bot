from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Awaitable, Callable, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Achievement, CurrencyTransaction, Duel, User, UserAchievement
from database.money_format import money_2
from database.repositories.currency_transaction_repository import CurrencyTransactionRepository
from database.transaction_reasons import achievement_reward_reason
from handlers.formatting import get_display_name
from logger import setup_logger
from services.slots_service import MULT_TRIPLE_SEVEN, SlotsPayout

logger = setup_logger(__name__)


@dataclass(frozen=True)
class AchievementDefinition:
    code: str
    title: str
    description: str
    category: str
    target_value: int
    reward_amount: float


ACHIEVEMENTS: tuple[AchievementDefinition, ...] = (
    AchievementDefinition("registration_first", "📝 Вписался в движ", "Зарегистрироваться в чате", "activity", 1, 50),
    AchievementDefinition("registration_return", "🔁 Вернулся в петушатник", "Вернуться после /unreg", "activity", 1, 100),
    AchievementDefinition("pidor_1", "🍍 Первый залет", "Стать пидором дня 1 раз", "pidor", 1, 100),
    AchievementDefinition("pidor_3", "🍩 Тройной петух", "Стать пидором дня 3 раза", "pidor", 3, 300),
    AchievementDefinition("pidor_10", "🧨 Десятый круг позора", "Стать пидором дня 10 раз", "pidor", 10, 1000),
    AchievementDefinition("pidor_25", "👑 Легенда петушатника", "Стать пидором дня 25 раз", "pidor", 25, 2500),
    AchievementDefinition("pidor_50", "💀 Полтинник позора", "Стать пидором дня 50 раз", "pidor", 50, 7500),
    AchievementDefinition("pidor_100", "🔥 Святой пидорасий", "Стать пидором дня 100 раз", "pidor", 100, 20000),
    AchievementDefinition("balance_1000", "🏦 Первая котлета", "Накопить 1 000 монет", "balance", 1000, 250),
    AchievementDefinition("balance_10000", "💰 Жирный кошелек", "Накопить 10 000 монет", "balance", 10000, 1500),
    AchievementDefinition("balance_100000", "🤑 Денежный монстр", "Накопить 100 000 монет", "balance", 100000, 10000),
    AchievementDefinition("slots_first_bet", "🎰 Дернул рычаг", "Сделать первую ставку в слотах", "slots", 1, 50),
    AchievementDefinition("slots_first_win", "🍋 Первая выплата", "Получить первый выигрыш в слотах", "slots", 1, 150),
    AchievementDefinition("slots_jackpot_1", "7️⃣ Джекпотный ублюдок", "Выбить три семерки", "slots", 1, 5000),
    AchievementDefinition("slots_profit_1000", "📈 Казино соснуло", "Выйти в плюс на 1 000 монет в слотах", "slots", 1000, 1000),
    AchievementDefinition("slots_loss_1000", "📉 Слил красиво", "Уйти в минус на 1 000 монет в слотах", "slots", 1000, 500),
    AchievementDefinition("slots_allin_win", "🚀 All-in выжил", "Победить после all-in в слотах", "slots", 1, 1000),
    AchievementDefinition("slots_allin_loss", "🕳 All-in в яму", "Проиграть all-in в слотах", "slots", 1, 300),
    AchievementDefinition("duel_first", "⚔️ Первый вызов", "Создать первую дуэль", "duels", 1, 100),
    AchievementDefinition("duel_first_win", "🏆 Первая кровь", "Выиграть первую дуэль", "duels", 1, 300),
    AchievementDefinition("duel_wins_5", "🗡 Пять заруб", "Выиграть 5 дуэлей", "duels", 5, 1000),
    AchievementDefinition("duel_wins_10", "🥇 Десять побед", "Выиграть 10 дуэлей", "duels", 10, 2500),
    AchievementDefinition("duel_big_win_1000", "💸 Большой куш", "Выиграть дуэль с выплатой от 1 000 монет", "duels", 1000, 1500),
    AchievementDefinition("duel_big_loss_1000", "🤕 Большой слив", "Проиграть дуэль на сумму от 1 000 монет", "duels", 1000, 500),
)

ACHIEVEMENT_BY_CODE = {achievement.code: achievement for achievement in ACHIEVEMENTS}


class AchievementService:
    @staticmethod
    async def ensure_catalog(session: AsyncSession) -> None:
        existing_result = await session.execute(select(Achievement))
        existing_by_code = {achievement.code: achievement for achievement in existing_result.scalars().all()}

        for definition in ACHIEVEMENTS:
            achievement = existing_by_code.get(definition.code)
            if achievement:
                achievement.title = definition.title
                achievement.description = definition.description
                achievement.category = definition.category
                achievement.target_value = definition.target_value
                achievement.reward_amount = definition.reward_amount
                achievement.is_active = True
            else:
                session.add(Achievement(
                    code=definition.code,
                    title=definition.title,
                    description=definition.description,
                    category=definition.category,
                    target_value=definition.target_value,
                    reward_amount=definition.reward_amount,
                    is_active=True,
                ))
        await session.flush()

    @staticmethod
    async def get_user_achievement_codes(session: AsyncSession, user_id: int) -> set[str]:
        result = await session.execute(
            select(Achievement.code)
            .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
            .where(UserAchievement.user_id == user_id)
        )
        return set(result.scalars().all())

    @staticmethod
    async def unlock(session: AsyncSession, user: User, code: str) -> Achievement | None:
        await AchievementService.ensure_catalog(session)
        result = await session.execute(select(Achievement).where(Achievement.code == code, Achievement.is_active.is_(True)))
        achievement = result.scalar_one_or_none()
        if not achievement:
            logger.warning("Unknown achievement code: %s", code)
            return None

        existing = await session.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user.id,
                UserAchievement.achievement_id == achievement.id,
            )
        )
        if existing.scalar_one_or_none():
            return None

        session.add(UserAchievement(
            user_id=user.id,
            achievement_id=achievement.id,
            unlocked_at=datetime.now(UTC),
        ))
        reward = money_2(achievement.reward_amount)
        user.balance = money_2(user.balance + reward)
        await CurrencyTransactionRepository.create_transaction(
            session,
            user.id,
            reward,
            achievement_reward_reason(achievement.code),
        )
        logger.info("Unlocked achievement %s for user_id=%s reward=%.2f", achievement.code, user.id, reward)
        return achievement

    @staticmethod
    async def unlock_many(session: AsyncSession, user: User, codes: Sequence[str]) -> list[Achievement]:
        unlocked = []
        for code in codes:
            achievement = await AchievementService.unlock(session, user, code)
            if achievement:
                unlocked.append(achievement)
        return unlocked

    @staticmethod
    async def notify(
            send_func: Callable[[str], Awaitable[None]],
            user: User,
            achievements: Sequence[Achievement],
    ) -> None:
        for achievement in achievements:
            await send_func(
                f"🎉 {get_display_name(user)} открыл достижение:\n"
                f"<b>{achievement.title}</b>\n"
                f"{achievement.description}\n"
                f"+{achievement.reward_amount:.2f} 🪙"
            )

    @staticmethod
    async def check_registration(session: AsyncSession, user: User, is_returning: bool) -> list[Achievement]:
        codes = ["registration_return" if is_returning else "registration_first"]
        return await AchievementService.unlock_many(session, user, codes)

    @staticmethod
    async def check_pidor(session: AsyncSession, user: User) -> list[Achievement]:
        codes = [definition.code for definition in ACHIEVEMENTS if definition.category == "pidor" and user.pidor_count >= definition.target_value]
        codes.extend(await AchievementService._balance_codes(user))
        return await AchievementService.unlock_many(session, user, codes)

    @staticmethod
    async def check_duel_created(session: AsyncSession, user: User) -> list[Achievement]:
        return await AchievementService.unlock_many(session, user, ["duel_first"])

    @staticmethod
    async def check_duel_finished(session: AsyncSession, winner: User, loser: User, amount: float, payout: float) -> tuple[list[Achievement], list[Achievement]]:
        winner_codes = ["duel_first_win"]
        wins = await AchievementService._duel_win_count(session, winner.id)
        if wins >= 5:
            winner_codes.append("duel_wins_5")
        if wins >= 10:
            winner_codes.append("duel_wins_10")
        if payout >= 1000:
            winner_codes.append("duel_big_win_1000")

        loser_codes = []
        if amount >= 1000:
            loser_codes.append("duel_big_loss_1000")

        winner_codes.extend(await AchievementService._balance_codes(winner))
        return (
            await AchievementService.unlock_many(session, winner, winner_codes),
            await AchievementService.unlock_many(session, loser, loser_codes),
        )

    @staticmethod
    async def check_slots(
            session: AsyncSession,
            user: User,
            bet: float,
            payout: SlotsPayout,
            is_all_in: bool,
            multiplier: float,
    ) -> list[Achievement]:
        codes = ["slots_first_bet"]
        if payout.net_win > 0:
            codes.append("slots_first_win")
        if multiplier == MULT_TRIPLE_SEVEN:
            codes.append("slots_jackpot_1")
        if is_all_in and payout.net_win > 0:
            codes.append("slots_allin_win")
        if is_all_in and payout.net_win <= 0:
            codes.append("slots_allin_loss")

        slot_bet, slot_win, slot_profit = await CurrencyTransactionRepository.get_slot_stats_for_user(session, user.id)
        if slot_profit >= 1000:
            codes.append("slots_profit_1000")
        if slot_profit <= -1000:
            codes.append("slots_loss_1000")
        codes.extend(await AchievementService._balance_codes(user))
        return await AchievementService.unlock_many(session, user, codes)

    @staticmethod
    async def _balance_codes(user: User) -> list[str]:
        return [
            definition.code
            for definition in ACHIEVEMENTS
            if definition.category == "balance" and user.balance >= definition.target_value
        ]

    @staticmethod
    async def _duel_win_count(session: AsyncSession, user_id: int) -> int:
        result = await session.execute(select(Duel).where(Duel.winner_id == user_id))
        return len(result.scalars().all())

    @staticmethod
    async def achievement_progress(session: AsyncSession, user: User, achievement: Achievement) -> int:
        if achievement.category == "pidor":
            return min(user.pidor_count, achievement.target_value)
        if achievement.category == "balance":
            return min(int(user.balance), achievement.target_value)
        if achievement.category == "slots":
            return min(await AchievementService._slots_progress(session, user.id, achievement.code), achievement.target_value)
        if achievement.category == "duels":
            return min(await AchievementService._duel_progress(session, user.id, achievement.code), achievement.target_value)
        if achievement.category == "activity":
            unlocked = await AchievementService.get_user_achievement_codes(session, user.id)
            return achievement.target_value if achievement.code in unlocked else 0
        return 0

    @staticmethod
    async def _slots_progress(session: AsyncSession, user_id: int, code: str) -> int:
        transactions = await CurrencyTransactionRepository.get_user_transactions(session, user_id)
        if code == "slots_first_bet":
            return int(any(tx.reason.startswith("slots_bet") or tx.reason == "slots bet" for tx in transactions))
        if code == "slots_first_win":
            return int(any(tx.reason.startswith("slots_win") or tx.reason == "slots win" for tx in transactions))
        if code == "slots_profit_1000":
            _, _, profit = await CurrencyTransactionRepository.get_slot_stats_for_user(session, user_id)
            return max(0, int(profit))
        if code == "slots_loss_1000":
            _, _, profit = await CurrencyTransactionRepository.get_slot_stats_for_user(session, user_id)
            return max(0, int(abs(min(profit, 0))))
        unlocked = await AchievementService.get_user_achievement_codes(session, user_id)
        return 1 if code in unlocked else 0

    @staticmethod
    async def _duel_progress(session: AsyncSession, user_id: int, code: str) -> int:
        if code == "duel_first":
            result = await session.execute(select(Duel).where(Duel.initiator_id == user_id))
            return int(bool(result.scalars().first()))
        if code in {"duel_first_win", "duel_wins_5", "duel_wins_10"}:
            return await AchievementService._duel_win_count(session, user_id)
        unlocked = await AchievementService.get_user_achievement_codes(session, user_id)
        return 1 if code in unlocked else 0
