import asyncio

from services.ai_response_buffer import AIResponseBuffer, AIService


async def test_ai_response_buffer_refills_unique_responses(monkeypatch, tmp_path):
    calls = 0

    async def fake_get_response(content, prompt):
        nonlocal calls
        calls += 1
        return f"response {calls}"

    monkeypatch.setattr(AIService, "get_response", fake_get_response)
    buffer = AIResponseBuffer(target_size=2, generation_concurrency=1, storage_path=tmp_path / "buffer.json")

    await buffer.refill_once()

    first = await buffer.pop("pidor_searching")
    second = await buffer.pop("pidor_searching")
    third = await buffer.pop("pidor_searching")

    assert first == "response 1"
    assert second == "response 2"
    assert third is None


async def test_ai_response_buffer_skips_duplicate_responses(monkeypatch, tmp_path):
    async def fake_get_response(content, prompt):
        return "same response"

    monkeypatch.setattr(AIService, "get_response", fake_get_response)
    buffer = AIResponseBuffer(target_size=2, generation_concurrency=1, storage_path=tmp_path / "buffer.json")

    await buffer.refill_once()

    assert await buffer.pop("pidor_win_phrase") == "same response"
    assert await buffer.pop("pidor_win_phrase") is None


async def test_ai_response_buffer_persists_between_instances(monkeypatch, tmp_path):
    async def fake_get_response(content, prompt):
        return "persisted response"

    storage_path = tmp_path / "buffer.json"
    monkeypatch.setattr(AIService, "get_response", fake_get_response)

    first_buffer = AIResponseBuffer(target_size=1, generation_concurrency=1, storage_path=storage_path)
    await first_buffer.refill_once()

    second_buffer = AIResponseBuffer(target_size=1, generation_concurrency=1, storage_path=storage_path)

    assert await second_buffer.pop("pidor_searching") == "persisted response"


async def test_ai_response_buffer_schedules_refill_after_pop(monkeypatch, tmp_path):
    responses = iter(["first", "second", "third"])

    async def fake_get_response(content, prompt):
        return next(responses)

    monkeypatch.setattr(AIService, "get_response", fake_get_response)
    buffer = AIResponseBuffer(target_size=1, generation_concurrency=1, storage_path=tmp_path / "buffer.json")
    await buffer.refill_key_once("pidor_searching")

    assert await buffer.pop("pidor_searching") == "first"
    await asyncio.sleep(0)

    assert await buffer.pop("pidor_searching") == "second"
