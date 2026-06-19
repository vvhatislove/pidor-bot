from datetime import datetime, UTC
from typing import Optional
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Index, Float, Text, UniqueConstraint, false
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from enum import Enum
from sqlalchemy import Enum as SQLEnum

Base = declarative_base()


class Chat(Base):
    """Модель чата/группы, где работает бот"""
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_chat_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        unique=True,
        index=True,
        doc="Telegram ID чата (отрицательный для групп)"
    )
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Название чата"
    )
    auto_pidor: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
        doc="Автоматический выбор пидора дня")
    # Связи
    users: Mapped[list["User"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    cooldown: Mapped["Cooldown"] = relationship(
        back_populates="chat",
        uselist=False,
        cascade="all, delete-orphan"
    )
    duels: Mapped[list["Duel"]] = relationship(back_populates="chat", cascade="all, delete-orphan")


class User(Base):
    """Модель пользователя в конкретном чате"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
        nullable=False,
        doc="ID пользователя в Telegram"
    )
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="Внутренний ID чата, к которому привязан пользователь"
    )

    # Данные пользователя
    first_name: Mapped[str] = mapped_column(String(100))
    username: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    registration_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )
    pidor_count: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Участвует ли пользователь в розыгрыше пидора дня"
    )
    is_admin: Mapped[bool] = mapped_column(default=False)
    fanfic_allowed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default=false(),
        doc="Разрешил ли пользователь хранить сообщения для /fanfic в этом чате"
    )
    balance: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Баланс внутриигровой валюты (может быть дробным)"
    )
    user_skills: Mapped[list["UserSkill"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    achievements: Mapped[list["UserAchievement"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    fanfic_messages: Mapped[list["FanficMessage"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    fanfic_usages: Mapped[list["FanficUsage"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # Связи
    chat: Mapped["Chat"] = relationship(back_populates="users")


    __table_args__ = (
        Index("ix_user_telegram_chat", "telegram_id", "chat_id", unique=True),
    )


class Cooldown(Base):
    """Настройки кулдауна для чата"""
    __tablename__ = "cooldowns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    last_activated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )
    cooldown_seconds: Mapped[int] = mapped_column(default=86400)
    pidor_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Пользователь, выбранный пидором дня в текущем кулдауне"
    )

    chat: Mapped["Chat"] = relationship(back_populates="cooldown")
    pidor_user: Mapped[Optional["User"]] = relationship(foreign_keys=[pidor_user_id])



class DuelStatus(str, Enum):
    WAITING_FOR_CONFIRMATION = "waiting_confirmation"
    ACTIVE = "active"        # Дуэль в процессе
    FINISHED = "finished"    # Дуэль завершена
    CANCELLED = "cancelled"  # Отменена (например, нет ставок)

class Duel(Base):
    __tablename__ = "duels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), index=True, nullable=False)

    initiator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    opponent_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    winner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Ставка дуэли между участниками"
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Время принятия дуэли оппонентом"
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Время начала дуэли"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )
    status: Mapped[DuelStatus] = mapped_column(
        SQLEnum(DuelStatus, name="duelstatus"),
        default=DuelStatus.WAITING_FOR_CONFIRMATION,
        nullable=False
    )
    initiator_win_chance: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Шанс победы инициатора (фиксируется при старте дуэли)",
        default=0.5
    )
    opponent_win_chance: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Шанс победы оппонента (1 - initiator)",
        default=0.5
    )

    # Optional: связи
    initiator: Mapped["User"] = relationship(foreign_keys=[initiator_id], lazy="selectin")
    opponent: Mapped["User"] = relationship(foreign_keys=[opponent_id], lazy="selectin")
    winner: Mapped[Optional["User"]] = relationship(foreign_keys=[winner_id], lazy="selectin")
    chat: Mapped["Chat"] = relationship(back_populates="duels")
    # bets: Mapped[list["Bet"]] = relationship(
    #     back_populates="duel",
    #     cascade="all, delete-orphan"
    # )


# class BetTarget(str, Enum):
#     INITIATOR = "initiator"
#     OPPONENT = "opponent"
#
# class Bet(Base):
#     """Ставка пользователя на дуэль"""
#     __tablename__ = "bets"
#
#     id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
#     duel_id: Mapped[int] = mapped_column(ForeignKey("duels.id", ondelete="CASCADE"), nullable=False)
#     user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
#
#     amount: Mapped[float] = mapped_column(Float, nullable=False, doc="Сумма ставки")
#     target: Mapped[BetTarget] = mapped_column(SQLEnum(BetTarget), nullable=False, doc="На кого сделана ставка")
#
#     created_at: Mapped[datetime] = mapped_column(
#         DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
#     )
#
#     # Связи
#     duel: Mapped["Duel"] = relationship(back_populates="bets")
#     user: Mapped["User"] = relationship()


class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_skills = relationship("UserSkill", back_populates="skill")

class UserSkill(Base):
    __tablename__ = "user_skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    level: Mapped[int] = mapped_column(default=1, nullable=False, doc="Уровень навыка (прокачивается за валюту)")

    user: Mapped["User"] = relationship(back_populates="user_skills")
    skill: Mapped["Skill"] = relationship(back_populates="user_skills")

    __table_args__ = (
        Index("ix_user_skill_unique", "user_id", "skill_id", unique=True),
    )


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    target_value: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_amount: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list["UserAchievement"]] = relationship(back_populates="achievement")


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id", ondelete="CASCADE"), index=True, nullable=False)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    user: Mapped["User"] = relationship(back_populates="achievements")
    achievement: Mapped["Achievement"] = relationship(back_populates="users")

    __table_args__ = (
        Index("ix_user_achievement_unique", "user_id", "achievement_id", unique=True),
    )


class FanficMessage(Base):
    __tablename__ = "fanfic_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    user: Mapped["User"] = relationship(back_populates="fanfic_messages")

    __table_args__ = (
        UniqueConstraint("user_id", "content_hash", name="uq_fanfic_message_user_hash"),
        Index("ix_fanfic_messages_user_created", "user_id", "created_at"),
    )


class FanficUsage(Base):
    __tablename__ = "fanfic_usages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    user: Mapped["User"] = relationship(back_populates="fanfic_usages")

    __table_args__ = (
        Index("ix_fanfic_usages_user_created", "user_id", "created_at"),
    )


class CurrencyTransaction(Base):
    __tablename__ = "currency_transactions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)  # например, "pidor_of_the_day"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user: Mapped["User"] = relationship()
