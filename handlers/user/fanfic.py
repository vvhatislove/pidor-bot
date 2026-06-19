import re
from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import AIPrompt, CommandText
from database.models import User
from database.repositories.user_repository import UserRepository
from logger import setup_logger
from services.ai_service import AIService
from services.fanfic_service import FANFIC_REQUIRED_MESSAGES, FANFIC_WEEKLY_LIMIT, FanficService
from services.time_service import format_local_datetime

logger = setup_logger(__name__)
router = Router()


_SENTENCE_END_RE = re.compile(r"(?<=[.!?…])\s+")


def _fanfic_context(messages: list[str]) -> str:
    return "\n".join(f"{index}. {text}" for index, text in enumerate(messages, 1))


def _format_fanfic_text(text: str, sentences_per_paragraph: int = 2) -> str:
    cleaned = "\n".join(line.strip() for line in text.strip().splitlines())
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if "\n\n" in cleaned:
        return cleaned

    sentences = [sentence.strip() for sentence in _SENTENCE_END_RE.split(cleaned) if sentence.strip()]
    if len(sentences) < 4:
        return cleaned

    paragraphs = [
        " ".join(sentences[index:index + sentences_per_paragraph])
        for index in range(0, len(sentences), sentences_per_paragraph)
    ]
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def _ensure_hero_tag(text: str, user: User) -> str:
    if not user.username:
        return text

    tag = f"@{user.username.lstrip('@')}"
    if tag.casefold() in text.casefold():
        return text
    return f"{tag}\n\n{text}"


def _fanfic_hero_name(user: User) -> str:
    if user.username:
        return f"@{user.username.lstrip('@')}"
    return user.first_name


def _fanfic_generation_context(user: User, messages: list[str]) -> str:
    return (
        f"Главный герой фанфика: {_fanfic_hero_name(user)}\n"
        "Ниже 100 сообщений главного героя из этого чата. Пиши фанфик именно про него. "
        "Если у героя есть @username, обязательно используй этот тег в тексте фанфика.\n\n"
        f"{_fanfic_context(messages)}"
    )


def _format_limit_datetime(value: datetime | None) -> str:
    if not value:
        return "позже"
    return format_local_datetime(value)


async def _get_group_user(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return None

    user = await UserRepository.get_user_by_telegram_id(session, message.from_user.id, message.chat.id)
    if not user:
        await message.answer("Сначала /reg прожми, герой без анкеты. Без регистрации фанфик не из чего лепить 💀")
        return None
    return user


@router.message(Command("allow_fanfic", "allowfanfic", ignore_case=True, ignore_mention=True))
async def cmd_allow_fanfic(message: Message, session: AsyncSession):
    user = await _get_group_user(message, session)
    if not user:
        return

    if user.fanfic_allowed:
        count = await FanficService.count_messages(session, user)
        await message.answer(
            "Писательский архив уже включён, не дёргай рубильник по десять раз 🤡\n"
            f"В копилке твоего словесного позора: {count}/{FANFIC_REQUIRED_MESSAGES} уникальных сообщений."
        )
        return

    await FanficService.set_allowed(session, user, True)
    await message.answer(
        "Принято, теперь я собираю твои уникальные высеры в этом чате для /fanfic 😈\n"
        f"Нужно набить {FANFIC_REQUIRED_MESSAGES} уникальных сообщений, потом сварю из них фанфик."
    )


@router.message(Command("deny_fanfic", "denyfanfic", ignore_case=True, ignore_mention=True))
async def cmd_deny_fanfic(message: Message, session: AsyncSession):
    user = await _get_group_user(message, session)
    if not user:
        return

    if not user.fanfic_allowed:
        await message.answer("Он и так выключен, архив молчит как побитый сервак 💀")
        return

    await FanficService.set_allowed(session, user, False)
    await message.answer(
        "Ок, новые сообщения больше не тащу в фанфик-архив 🧹\n"
        "Старый компромат в базе остаётся, историю уже не отмыть."
    )


@router.message(Command("fanfic", ignore_case=True, ignore_mention=True))
async def cmd_fanfic(message: Message, session: AsyncSession):
    user = await _get_group_user(message, session)
    if not user:
        return

    if not user.fanfic_allowed:
        await message.answer("Сначала разреши сбор командой /allow_fanfic, а потом уже требуй литературный разврат 📖")
        return

    count = await FanficService.count_messages(session, user)
    if count < FANFIC_REQUIRED_MESSAGES:
        await message.answer(
            "Материала пока мало, из трёх твоих фраз роман не слепишь 🤡\n"
            f"Собрано уникального словесного топлива: {count}/{FANFIC_REQUIRED_MESSAGES}."
        )
        return

    remaining_usages = await FanficService.remaining_weekly_usages(session, user)
    if remaining_usages <= 0:
        next_available_at = await FanficService.next_available_at(session, user)
        await message.answer(
            f"Лимит фанфиков на неделю выбит в ноль: {FANFIC_WEEKLY_LIMIT}/{FANFIC_WEEKLY_LIMIT} 💀\n"
            f"Следующий литературный разврат будет доступен после {_format_limit_datetime(next_available_at)}."
        )
        return

    messages = await FanficService.get_context_messages(session, user)
    context = _fanfic_generation_context(user, [item.content for item in messages])
    await message.answer(
        "Листаю твой чатный позор и пишу фанфик, держись за жопу 📖😈\n"
        f"Осталось попыток на неделю после этой: {remaining_usages - 1}/{FANFIC_WEEKLY_LIMIT}."
    )
    fanfic = await AIService.get_response(
        content=context,
        ai_prompt=AIPrompt.FANFIC_PROMPT,
        include_style_suffix=False,
    )
    if not fanfic:
        await message.answer("Фанфик не родился: модель опять упала лицом в цензурную подушку 💀")
        return

    await FanficService.record_successful_generation(session, user)
    logger.info("Generated fanfic for user %s in chat %s", user.telegram_id, message.chat.id)
    await message.answer(_ensure_hero_tag(_format_fanfic_text(fanfic), user))
