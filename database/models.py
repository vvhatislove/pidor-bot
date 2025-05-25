from datetime import datetime, UTC
from typing import Optional
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column

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
