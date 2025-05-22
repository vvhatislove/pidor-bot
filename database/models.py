from datetime import datetime, UTC
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    chat_id: Mapped[int] = mapped_column(Integer, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    username: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    registration_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(UTC),
        doc="Дата и время регистрации пользователя"
    )
    pidor_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Количество раз, когда пользователь был выбран пидором дня"
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        doc="Является ли пользователь администратором бота"
    )

    # Составной индекс для часто используемых запросов
    __table_args__ = (
        Index('ix_user_telegram_chat', 'telegram_id', 'chat_id', unique=True),
    )


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(
        String(100),
        doc="Название чата для удобного отображения"
    )

    # Отношение один-к-одному с Cooldown
    cooldown: Mapped["Cooldown"] = relationship(
        "Cooldown",
        back_populates="chat",
        uselist=False,
        cascade="all, delete-orphan"
    )


class Cooldown(Base):
    __tablename__ = "cooldowns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('chats.id', ondelete="CASCADE"),
        unique=True,
        doc="Ссылка на чат, для которого установлен кулдаун"
    )
    last_activated: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(UTC),
        doc="Время последней активации команды /pidor"
    )
    cooldown_seconds: Mapped[int] = mapped_column(
        Integer,
        default=86400,  # 24 часа
        doc="Длительность кулдауна в секундах"
    )

    # Обратная ссылка на чат
    chat: Mapped["Chat"] = relationship(
        "Chat",
        back_populates="cooldown"
    )