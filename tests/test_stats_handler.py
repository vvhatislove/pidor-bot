from types import SimpleNamespace

from database.repositories.chat_repository import ChatRepository
from database.repositories.user_repository import UserRepository
from handlers.user.stats import cmd_stats


class FakeMessage:
    def __init__(self):
        self.chat = SimpleNamespace(id=-100, type="group", title="chat")
        self.from_user = SimpleNamespace(id=1)
        self.answers = []

    async def answer(self, text: str, **kwargs):
        self.answers.append(text)


async def test_stats_shows_balance_and_inactive_participation_status(session):
    await ChatRepository.create_chat(session, -100, "chat")
    active = await UserRepository.create_user(session, 1, -100, "Active", "active")
    inactive = await UserRepository.create_user(session, 2, -100, "Inactive", "inactive")
    active.balance = 123.45
    active.pidor_count = 2
    inactive.balance = 50
    inactive.pidor_count = 1
    await UserRepository.deactivate_user(session, inactive)
    await session.commit()

    message = FakeMessage()

    await cmd_stats(message, session)

    assert len(message.answers) == 1
    text = message.answers[0]
    assert "active — 2 раз(а)" in text
    assert "баланс: 123.45 🪙" in text
    assert "inactive (не участвует в розыгрыше) — 1 раз(а)" in text
    assert "баланс: 50.00 🪙" in text
