import asyncio

from database.repositories.chat_repository import ChatRepository
from database.repositories.cooldown_repository import CooldownRepository
from database.repositories.currency_transaction_repository import CurrencyTransactionRepository
from database.repositories.user_repository import UserRepository
from services import auto_pidor_service
from services.ai_service import AIService
from services.pidor_service import (
    _format_win_phrase,
    _search_phrases_from_ai_response,
    run_pidor_selection,
)


async def _send_collector(messages):
    async def send(chat_id, text, *args, **kwargs):
        messages.append((chat_id, text))

    return send


async def _create_registered_user(session, chat_id: int, telegram_id: int = 1):
    await ChatRepository.create_chat(session, chat_id, "chat")
    return await UserRepository.create_user(
        session=session,
        telegram_id=telegram_id,
        chat_telegram_id=chat_id,
        first_name="User",
        username="user",
    )


def test_search_phrases_from_ai_response_ignores_empty_parts():
    phrases = _search_phrases_from_ai_response("first | | second | third")

    assert phrases == ["first", "second"]


def test_format_win_phrase_recovers_from_bad_ai_template():
    phrase = _format_win_phrase("bad {missing}", "@user")

    assert "@user" in phrase


async def test_run_pidor_selection_awards_user_and_sets_cooldown(monkeypatch, session):
    user = await _create_registered_user(session, -100)
    messages = []

    async def fake_get_response(content, ai_prompt, **kwargs):
        if "|" in ai_prompt:
            return "search one|search two"
        return "winner is {name}"

    async def fake_sleep(seconds):
        return None

    async def empty_buffer_pop(key):
        return None

    monkeypatch.setattr(AIService, "get_response", fake_get_response)
    monkeypatch.setattr("services.pidor_service.ai_response_buffer.pop", empty_buffer_pop)
    monkeypatch.setattr("services.pidor_service.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("services.pidor_service.random.choice", lambda values: values[0])

    await run_pidor_selection(
        chat_id=-100,
        send_func=await _send_collector(messages),
        session=session,
        is_automatic=False,
    )

    assert user.pidor_count == 1
    assert user.balance == 100
    cooldown = await CooldownRepository.get_cooldown(session, -100)
    assert cooldown is not None
    assert cooldown.pidor_user_id == user.id

    transactions = await CurrencyTransactionRepository.get_user_transactions(session, user.id)
    assert len(transactions) == 1
    assert transactions[0].amount == 100

    sent_texts = [text for _, text in messages]
    assert sent_texts[:3] == ["Так так так... Погодите-ка...🔍", "search one", "search two"]
    assert "winner is @user" in sent_texts[3]


async def test_run_pidor_selection_respects_same_day_cooldown(monkeypatch, session):
    user = await _create_registered_user(session, -100)
    await CooldownRepository.set_cooldown(session, -100)
    messages = []

    async def fail_get_response(*args, **kwargs):
        raise AssertionError("AI should not be called during cooldown")

    monkeypatch.setattr(AIService, "get_response", fail_get_response)

    await run_pidor_selection(
        chat_id=-100,
        send_func=await _send_collector(messages),
        session=session,
        is_automatic=False,
    )

    assert user.pidor_count == 0
    assert user.balance == 0
    assert len(messages) == 1
    assert "уже известен" in messages[0][1]


async def test_run_pidor_selection_shows_today_pidor_username_during_cooldown(monkeypatch, session):
    user = await _create_registered_user(session, -100)
    await CooldownRepository.set_cooldown(session, -100, pidor_user_id=user.id)
    messages = []

    async def fail_get_response(*args, **kwargs):
        raise AssertionError("AI should not be called during cooldown")

    monkeypatch.setattr(AIService, "get_response", fail_get_response)

    await run_pidor_selection(
        chat_id=-100,
        send_func=await _send_collector(messages),
        session=session,
        is_automatic=False,
    )

    assert len(messages) == 1
    assert "уже известен: @user" in messages[0][1]


async def test_run_pidor_selection_excludes_inactive_users(monkeypatch, session):
    active_user = await _create_registered_user(session, -100, telegram_id=1)
    inactive_user = await UserRepository.create_user(
        session=session,
        telegram_id=2,
        chat_telegram_id=-100,
        first_name="Inactive",
        username="inactive",
    )
    await UserRepository.deactivate_user(session, inactive_user)
    messages = []

    async def fake_get_response(content, ai_prompt, **kwargs):
        if "|" in ai_prompt:
            return "search one|search two"
        return "winner is {name}"

    async def fake_sleep(seconds):
        return None

    async def empty_buffer_pop(key):
        return None

    def pick_first_active(values):
        assert inactive_user not in values
        assert active_user in values
        return values[0]

    monkeypatch.setattr(AIService, "get_response", fake_get_response)
    monkeypatch.setattr("services.pidor_service.ai_response_buffer.pop", empty_buffer_pop)
    monkeypatch.setattr("services.pidor_service.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("services.pidor_service.random.choice", pick_first_active)

    await run_pidor_selection(
        chat_id=-100,
        send_func=await _send_collector(messages),
        session=session,
        is_automatic=False,
    )

    assert active_user.pidor_count == 1
    assert inactive_user.pidor_count == 0


async def test_auto_pidor_runs_all_enabled_chats_even_if_one_fails(monkeypatch, session_factory):
    async with session_factory() as session:
        first = await ChatRepository.create_chat(session, -100, "first")
        second = await ChatRepository.create_chat(session, -200, "second")
        first.auto_pidor = True
        second.auto_pidor = True
        await session.commit()

    attempted = []

    async def fake_run_pidor_selection(chat_id, send_func, session, is_automatic):
        attempted.append(chat_id)
        if chat_id == -100:
            raise RuntimeError("first chat failed")

    monkeypatch.setattr(auto_pidor_service, "run_pidor_selection", fake_run_pidor_selection)

    class Bot:
        async def send_message(self, *args, **kwargs):
            return None

    await auto_pidor_service.run_pidor_for_all(Bot(), session_factory)

    assert set(attempted) == {-100, -200}


async def test_auto_pidor_limits_parallel_chat_runs(monkeypatch, session_factory):
    chat_ids = [-100, -200, -300, -400]
    async with session_factory() as session:
        for chat_id in chat_ids:
            chat = await ChatRepository.create_chat(session, chat_id, f"chat {chat_id}")
            chat.auto_pidor = True
        await session.commit()

    active = 0
    max_active = 0

    async def fake_run_pidor_selection(chat_id, send_func, session, is_automatic):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1

    monkeypatch.setattr(auto_pidor_service, "AUTO_PIDOR_CONCURRENCY", 2)
    monkeypatch.setattr(auto_pidor_service, "run_pidor_selection", fake_run_pidor_selection)

    class Bot:
        async def send_message(self, *args, **kwargs):
            return None

    await auto_pidor_service.run_pidor_for_all(Bot(), session_factory)

    assert max_active == 2


async def test_new_chat_does_not_enable_auto_pidor_by_default(session):
    await ChatRepository.create_chat(session, -100, "chat")

    chats = await ChatRepository.get_auto_pidor_chats(session)

    assert chats == []
