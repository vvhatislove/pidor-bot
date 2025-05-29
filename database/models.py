from datetime import datetime, UTC
from typing import Optional
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Index, Float
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from enum import Enum
from sqlalchemy import Enum as SQLEnum

Base = declarative_base()


class Chat(Base):
    """Модель чата/группы, где работает бот"""
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
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
    is_admin: Mapped[bool] = mapped_column(default=False)
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

    chat: Mapped["Chat"] = relationship(back_populates="cooldown")



class DuelStatus(str, Enum):
    PENDING = "pending"      # Идёт приём ставок
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

    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Время начала дуэли (после ставок)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )
    status: Mapped[DuelStatus] = mapped_column(
        SQLEnum(DuelStatus, name="duelstatus"),
        default=DuelStatus.PENDING,
        nullable=False
    )
    initiator_win_chance: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Шанс победы инициатора (фиксируется при старте дуэли)"
    )
    opponent_win_chance: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Шанс победы оппонента (1 - initiator)"
    )

    # Optional: связи
    initiator: Mapped["User"] = relationship(foreign_keys=[initiator_id])
    opponent: Mapped["User"] = relationship(foreign_keys=[opponent_id])
    winner: Mapped[Optional["User"]] = relationship(foreign_keys=[winner_id])
    chat: Mapped["Chat"] = relationship()
    bets: Mapped[list["Bet"]] = relationship(
        back_populates="duel",
        cascade="all, delete-orphan"
    )


class BetTarget(str, Enum):
    INITIATOR = "initiator"
    OPPONENT = "opponent"

class Bet(Base):
    """Ставка пользователя на дуэль"""
    __tablename__ = "bets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    duel_id: Mapped[int] = mapped_column(ForeignKey("duels.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    amount: Mapped[int] = mapped_column(nullable=False, doc="Сумма ставки")
    target: Mapped[BetTarget] = mapped_column(SQLEnum(BetTarget), nullable=False, doc="На кого сделана ставка")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Связи
    duel: Mapped["Duel"] = relationship(back_populates="bets")
    user: Mapped["User"] = relationship()


class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

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


class CurrencyTransaction(Base):
    __tablename__ = "currency_transactions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[int] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)  # например, "pidor_of_the_day"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user: Mapped["User"] = relationship()