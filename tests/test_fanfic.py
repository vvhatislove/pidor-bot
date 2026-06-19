from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from database.repositories.fanfic_usage_repository import FanficUsageRepository
from database.repositories.chat_repository import ChatRepository
from database.repositories.user_repository import UserRepository
from handlers.user.fanfic import _ensure_hero_tag, _format_fanfic_text, cmd_allow_fanfic, cmd_fanfic
from services.fanfic_service import FANFIC_REQUIRED_MESSAGES, FANFIC_WEEKLY_LIMIT, FanficService


class FakeMessage:
    def __init__(self, text: str, chat_id: int = -100, chat_type: str = "group", from_user_id: int = 1):
        self.text = text
        self.chat = SimpleNamespace(id=chat_id, type=chat_type, title="chat")
        self.from_user = SimpleNamespace(id=from_user_id, first_name="User", username="user")
        self.answers = []

    async def answer(self, text: str, **kwargs):
        self.answers.append(text)


async def _create_user(session):
    await ChatRepository.create_chat(session, -100, "chat")
    return await UserRepository.create_user(session, 1, -100, "User", "user")


async def test_allow_fanfic_enables_collection_for_registered_user(session):
    user = await _create_user(session)
    message = FakeMessage("/allow_fanfic")

    await cmd_allow_fanfic(message, session)

    assert user.fanfic_allowed is True
    assert "собираю твои уникальные" in message.answers[0]


async def test_fanfic_message_storage_is_unique_and_limited(session):
    user = await _create_user(session)
    await FanficService.set_allowed(session, user, True)

    assert await FanficService.store_user_message(session, user, "  Первый   текст  ") is True
    assert await FanficService.store_user_message(session, user, "первый текст") is False

    for index in range(1, 101):
        await FanficService.store_user_message(session, user, f"уникальное сообщение {index}")

    messages = await FanficService.get_context_messages(session, user)
    assert len(messages) == 100
    assert all(item.content != "Первый текст" for item in messages)
    assert messages[-1].content == "уникальное сообщение 100"


async def test_fanfic_command_requires_full_message_buffer(session):
    user = await _create_user(session)
    await FanficService.set_allowed(session, user, True)
    await FanficService.store_user_message(session, user, "слишком мало материала")
    message = FakeMessage("/fanfic")

    await cmd_fanfic(message, session)

    assert f"1/{FANFIC_REQUIRED_MESSAGES}" in message.answers[0]


async def test_fanfic_command_generates_from_saved_messages(session, monkeypatch):
    user = await _create_user(session)
    await FanficService.set_allowed(session, user, True)
    for index in range(FANFIC_REQUIRED_MESSAGES):
        await FanficService.store_user_message(session, user, f"сообщение для фанфика {index}")

    calls = {}

    async def fake_get_response(content, ai_prompt, **kwargs):
        calls["content"] = content
        calls["kwargs"] = kwargs
        return "Готовый фанфик"

    monkeypatch.setattr("handlers.user.fanfic.AIService.get_response", fake_get_response)
    message = FakeMessage("/fanfic")

    await cmd_fanfic(message, session)

    assert message.answers == [
        "Листаю твой чатный позор и пишу фанфик, держись за жопу 📖😈\n"
        "Осталось попыток на неделю после этой: 2/3.",
        "@user\n\nГотовый фанфик",
    ]
    assert "Главный герой фанфика: @user" in calls["content"]
    assert "Пиши фанфик именно про него" in calls["content"]
    assert "обязательно используй этот тег" in calls["content"]
    assert "1. сообщение для фанфика 0" in calls["content"]
    assert "100. сообщение для фанфика 99" in calls["content"]
    assert calls["kwargs"]["include_style_suffix"] is False
    assert await FanficService.count_recent_usages(session, user) == 1


async def test_fanfic_command_blocks_after_three_successful_generations(session, monkeypatch):
    user = await _create_user(session)
    await FanficService.set_allowed(session, user, True)
    for index in range(FANFIC_REQUIRED_MESSAGES):
        await FanficService.store_user_message(session, user, f"сообщение для фанфика {index}")
    now = datetime.now(UTC)
    for index in range(FANFIC_WEEKLY_LIMIT):
        await FanficUsageRepository.create_usage(session, user.id, now - timedelta(days=index))
    await session.commit()

    async def fake_get_response(*args, **kwargs):
        raise AssertionError("AI should not be called when fanfic limit is exhausted")

    monkeypatch.setattr("handlers.user.fanfic.AIService.get_response", fake_get_response)
    message = FakeMessage("/fanfic")

    await cmd_fanfic(message, session)

    assert "Лимит фанфиков на неделю выбит в ноль" in message.answers[0]
    assert "3/3" in message.answers[0]


async def test_fanfic_failed_generation_does_not_consume_weekly_usage(session, monkeypatch):
    user = await _create_user(session)
    await FanficService.set_allowed(session, user, True)
    for index in range(FANFIC_REQUIRED_MESSAGES):
        await FanficService.store_user_message(session, user, f"сообщение для фанфика {index}")

    async def fake_get_response(*args, **kwargs):
        return ""

    monkeypatch.setattr("handlers.user.fanfic.AIService.get_response", fake_get_response)
    message = FakeMessage("/fanfic")

    await cmd_fanfic(message, session)

    assert "Фанфик не родился" in message.answers[-1]
    assert await FanficService.count_recent_usages(session, user) == 0


def test_format_fanfic_text_splits_long_plain_text_into_paragraphs():
    text = (
        "Первое предложение. Второе предложение. Третье предложение. "
        "Четвёртое предложение. Пятое предложение. Шестое предложение."
    )

    formatted = _format_fanfic_text(text)

    assert formatted.count("\n\n") == 2
    assert "Первое предложение. Второе предложение.\n\nТретье предложение." in formatted


def test_format_fanfic_text_preserves_existing_paragraphs():
    text = "Первый абзац.\n\nВторой абзац."

    assert _format_fanfic_text(text) == text


async def test_ensure_hero_tag_adds_username_when_model_omits_it(session):
    user = await _create_user(session)

    assert _ensure_hero_tag("Готовый фанфик", user) == "@user\n\nГотовый фанфик"


async def test_ensure_hero_tag_does_not_duplicate_existing_username(session):
    user = await _create_user(session)

    assert _ensure_hero_tag("@user уже главный герой", user) == "@user уже главный герой"
