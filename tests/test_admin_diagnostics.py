from datetime import datetime
from types import SimpleNamespace

from config.config import config
from database.repositories.chat_repository import ChatRepository
from database.repositories.cooldown_repository import CooldownRepository
from database.repositories.user_repository import UserRepository
from handlers.admin.diagnostics import cb_chats_page, cmd_admin_stats, cmd_chat_info, cmd_chats, cmd_reset_pidor_today
from handlers.admin.distribution import (
    ANNOUNCE_CONFIRM_CALLBACK,
    ANNOUNCE_EDIT_CALLBACK,
    cmd_announce_update,
    cb_announce_update_confirm,
    cb_announce_update_edit,
)
from handlers.user.common import help_start


class FakeMessage:
    def __init__(
        self,
        text: str,
        chat_id: int = -100,
        chat_type: str = "group",
        from_user_id: int | None = None,
        bot=None,
    ):
        self.text = text
        self.chat = SimpleNamespace(id=chat_id, type=chat_type, title="chat")
        self.from_user = SimpleNamespace(id=from_user_id or config.ADMIN_ID, first_name="Admin", username="admin")
        self.bot = bot
        self.answers = []
        self.answer_kwargs = []
        self.documents = []

    async def answer(self, text: str, **kwargs):
        self.answers.append(text)
        self.answer_kwargs.append(kwargs)

    async def answer_document(self, document, **kwargs):
        self.documents.append((document, kwargs))


class FakeCallbackMessage:
    def __init__(self, bot=None):
        self.bot = bot
        self.edits = []
        self.answers = []

    async def edit_text(self, text: str, **kwargs):
        self.edits.append((text, kwargs))

    async def answer(self, text: str, **kwargs):
        self.answers.append((text, kwargs))


class FakeCallback:
    def __init__(self, data: str, from_user_id: int | None = None, bot=None):
        self.data = data
        self.from_user = SimpleNamespace(id=from_user_id or config.ADMIN_ID)
        self.message = FakeCallbackMessage(bot=bot)
        self.answers = []

    async def answer(self, *args, **kwargs):
        self.answers.append((args, kwargs))


class FakeBot:
    def __init__(self, fail_chat_ids: set[int] | None = None):
        self.fail_chat_ids = fail_chat_ids or set()
        self.sent_messages = []

    async def send_message(self, chat_id: int, text: str, **kwargs):
        if chat_id in self.fail_chat_ids:
            raise RuntimeError("send failed")
        self.sent_messages.append((chat_id, text, kwargs))


async def test_admin_help_contains_only_group_admin_commands_in_group():
    message = FakeMessage("/help", chat_type="group")

    await help_start(message)

    assert "/chat_info" in message.answers[0]
    assert "/addbalance" in message.answers[0]
    assert "/admin_stats" not in message.answers[0]
    assert "/backup_now" not in message.answers[0]


async def test_admin_help_contains_private_admin_commands_in_private():
    message = FakeMessage("/help", chat_id=config.ADMIN_ID, chat_type="private")

    await help_start(message)

    assert "/admin_stats" in message.answers[0]
    assert "/backup_now" in message.answers[0]
    assert "/announce_update [текст]" in message.answers[0]
    assert "/chat_info chat_id" in message.answers[0]
    assert "/addbalance" not in message.answers[0]


async def test_regular_help_does_not_show_admin_commands():
    message = FakeMessage("/help", chat_type="group", from_user_id=config.ADMIN_ID + 1)

    await help_start(message)

    assert "/admin_stats" not in message.answers[0]


async def test_announce_update_private_preview_does_not_send_immediately():
    bot = FakeBot()
    message = FakeMessage(
        "/announce_update Новый релиз уже в чате",
        chat_id=config.ADMIN_ID,
        chat_type="private",
        bot=bot,
    )

    await cmd_announce_update(message)

    assert "Превью рассылки обновления" in message.answers[0]
    assert "Новый релиз уже в чате" in message.answers[0]
    assert bot.sent_messages == []
    keyboard = message.answer_kwargs[0]["reply_markup"]
    assert keyboard.inline_keyboard[0][0].callback_data == ANNOUNCE_CONFIRM_CALLBACK


async def test_announce_update_group_is_rejected():
    message = FakeMessage("/announce_update")

    await cmd_announce_update(message)

    assert "только в ЛС" in message.answers[0]


async def test_announce_update_edit_button_explains_custom_command():
    callback = FakeCallback(ANNOUNCE_EDIT_CALLBACK)

    await cb_announce_update_edit(callback)

    assert "/announce_update текст сообщения" in callback.message.answers[0][0]


async def test_announce_update_confirm_sends_to_chats_and_counts_failures(session):
    await ChatRepository.create_chat(session, -100, "first")
    await ChatRepository.create_chat(session, -200, "second")
    bot = FakeBot(fail_chat_ids={-200})
    message = FakeMessage(
        "/announce_update Релиз установлен",
        chat_id=config.ADMIN_ID,
        chat_type="private",
        bot=bot,
    )
    await cmd_announce_update(message)
    callback = FakeCallback(ANNOUNCE_CONFIRM_CALLBACK, bot=bot)

    await cb_announce_update_confirm(callback, session)

    assert bot.sent_messages == [(-100, "Релиз установлен", {})]
    assert "Успешно: 1" in callback.message.edits[0][0]
    assert "Ошибок: 1" in callback.message.edits[0][0]


async def test_admin_stats_private_summary(session):
    await ChatRepository.create_chat(session, -100, "chat")
    await UserRepository.create_user(session, 1, -100, "User", "user")
    message = FakeMessage("/admin_stats", chat_id=config.ADMIN_ID, chat_type="private")

    await cmd_admin_stats(message, session)

    assert "Админ-статистика" in message.answers[0]
    assert "Чатов: <b>1</b>" in message.answers[0]
    assert "Пользователей: <b>1</b>" in message.answers[0]


async def test_chats_private_summary_is_paginated(session):
    first_chat = await ChatRepository.create_chat(session, -100, "first")
    await ChatRepository.create_chat(session, -200, "second")
    first_user = await UserRepository.create_user(session, 1, -100, "One", "one")
    second_user = await UserRepository.create_user(session, 2, -100, "Two", "two")
    first_user.balance = 100
    second_user.balance = 250.55
    await UserRepository.deactivate_user(session, second_user)
    await session.commit()
    message = FakeMessage("/chats 1 1", chat_id=config.ADMIN_ID, chat_type="private")

    await cmd_chats(message, session)

    assert "страница <b>1/2</b>" in message.answers[0]
    assert "Название: <b>first</b>" in message.answers[0]
    assert f"ID: <code>{first_chat.telegram_chat_id}</code>" in message.answers[0]
    assert "участников: <b>2</b> (активных: <b>1</b>)" in message.answers[0]
    assert "350.55 🪙" in message.answers[0]
    keyboard = message.answer_kwargs[0]["reply_markup"]
    assert keyboard.inline_keyboard[0][1].text == "1/2"
    assert keyboard.inline_keyboard[0][2].callback_data == "admin_chats:2:1"


async def test_chats_callback_switches_page(session):
    await ChatRepository.create_chat(session, -100, "first")
    second_chat = await ChatRepository.create_chat(session, -200, "second")
    callback = FakeCallback("admin_chats:2:1")

    await cb_chats_page(callback, session)

    assert len(callback.message.edits) == 1
    text, kwargs = callback.message.edits[0]
    assert "страница <b>2/2</b>" in text
    assert "Название: <b>second</b>" in text
    assert f"ID: <code>{second_chat.telegram_chat_id}</code>" in text
    assert kwargs["reply_markup"].inline_keyboard[0][0].callback_data == "admin_chats:1:1"


async def test_chat_info_uses_current_group_chat(session):
    await ChatRepository.create_chat(session, -100, "chat")
    user = await UserRepository.create_user(session, 1, -100, "User", "user")
    await CooldownRepository.set_cooldown(session, -100, pidor_user_id=user.id)
    message = FakeMessage("/chat_info", chat_id=-100, chat_type="group")

    await cmd_chat_info(message, session)

    assert "Chat info" in message.answers[0]
    assert "Telegram ID: <code>-100</code>" in message.answers[0]
    assert "@user" in message.answers[0]


async def test_chat_info_formats_cooldown_time_in_config_timezone(session):
    await ChatRepository.create_chat(session, -100, "chat")
    await CooldownRepository.set_cooldown(session, -100)
    cooldown = await CooldownRepository.get_cooldown(session, -100)
    cooldown.last_activated = datetime(2026, 6, 15, 10, 0)
    await session.commit()
    message = FakeMessage("/chat_info", chat_id=-100, chat_type="group")

    await cmd_chat_info(message, session)

    assert "Последний запуск: <b>15.06.2026 13:00</b>" in message.answers[0]


async def test_reset_pidor_today_is_private_only_and_deletes_cooldown(session):
    await ChatRepository.create_chat(session, -100, "chat")
    await CooldownRepository.set_cooldown(session, -100)

    group_message = FakeMessage("/reset_pidor_today", chat_id=-100, chat_type="group")
    await cmd_reset_pidor_today(group_message, session)
    assert "ЛС" in group_message.answers[0]
    assert await CooldownRepository.get_cooldown(session, -100) is not None

    private_message = FakeMessage("/reset_pidor_today -100", chat_id=config.ADMIN_ID, chat_type="private")
    await cmd_reset_pidor_today(private_message, session)
    assert "Сброшено cooldown-записей" in private_message.answers[0]
    assert await CooldownRepository.get_cooldown(session, -100) is None
