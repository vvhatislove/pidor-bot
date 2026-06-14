from types import SimpleNamespace

from services.ai_service import clean_model_response, is_bad_model_response, is_blocked_completion


def test_rejects_cjk_role_break_response():
    text = "作为一个人工智能语言模型，我还没学习如何回答这个问题。"

    assert is_bad_model_response(text)


def test_rejects_refusal_response():
    assert is_bad_model_response("Извините, я не могу помочь с этим запросом.")
    assert is_bad_model_response("As an AI, I can't assist with that.")


def test_rejects_euphemism_response():
    assert is_bad_model_response("Обнаружен подозрительный объект с радужным флагом.")
    assert is_bad_model_response("Даже радуга покраснела от твоего пидорства.")
    assert is_bad_model_response("Нюхаешь радужные трусы в петушатнике.")


def test_clean_model_response_removes_outer_quotes():
    assert clean_model_response('"Фраза без кавычек"') == "Фраза без кавычек"
    assert clean_model_response("«Первая»\n“Вторая”") == "Первая\nВторая"


def test_clean_model_response_removes_parenthetical_meta_comments():
    assert clean_model_response(
        "Готовая реплика для чата 💀 (условия выполнены: одно предложение, без кавычек)"
    ) == "Готовая реплика для чата 💀"
    assert clean_model_response("(образ создан, соответствует промпту)") == ""


def test_accepts_normal_russian_response():
    assert not is_bad_model_response("О, смотрите, очередной диванный герой решил блеснуть мозгами 💀")


def test_detects_blocked_completion_finish_reason():
    response = SimpleNamespace(
        choices=[SimpleNamespace(finish_reason="content_filter")],
        moderation=None,
    )

    assert is_blocked_completion(response)


def test_detects_blocked_completion_moderation_flag():
    response = SimpleNamespace(
        choices=[SimpleNamespace(finish_reason="stop")],
        moderation={"flagged": True},
    )

    assert is_blocked_completion(response)


def test_accepts_normal_completion_metadata():
    response = SimpleNamespace(
        choices=[SimpleNamespace(finish_reason="stop")],
        moderation=None,
    )

    assert not is_blocked_completion(response)
