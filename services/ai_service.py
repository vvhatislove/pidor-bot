import asyncio
import re

from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from config.config import config
from config.constants import LLMDefaults
from logger import setup_logger

logger = setup_logger(__name__)

_REFUSAL_PATTERNS = [
    r"\b(?:i|i'm|i am)\s+(?:sorry|unable|not able|cannot|can't)\b",
    r"\bas an ai\b",
    r"\bi (?:can't|cannot|won't) (?:help|assist|provide)\b",
    r"\bне могу\b",
    r"\bне буду\b",
    r"\bизвин",
    r"\bя не знаю\b",
    r"\bне располагаю\b",
    r"\bне могу помочь\b",
    r"\bя .*(?:ии|искусственн)",
    r"我不能",
    r"我无法",
    r"抱歉",
    r"对不起",
]

_BANNED_EUPHEMISMS = [
    "кринжовый",
    "звёздный час",
    "звездный час",
    "флагман",
    "подозрительный объект",
]

_BANNED_EUPHEMISM_PATTERNS = [
    re.compile(r"\bрадуг\w*", re.IGNORECASE),
    re.compile(r"\bрадуж\w*", re.IGNORECASE),
]

_META_COMMENT_PATTERN = re.compile(
    r"(?:услов|выполн|требован|промпт|формат|роль|пояснен|пояснён|"
    r"placeholder|плейсхолдер|кавыч|соблюд|соответств|образ создан)",
    re.IGNORECASE,
)


def _strip_meta_parenthetical(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith(("(", "[")) and stripped.endswith((")", "]")) and _META_COMMENT_PATTERN.search(stripped):
        return ""
    return re.sub(r"\s*[\(\[][^\)\]]{0,220}[\)\]]\s*$", _remove_meta_match, stripped)


def _remove_meta_match(match: re.Match[str]) -> str:
    value = match.group(0)
    return "" if _META_COMMENT_PATTERN.search(value) else value


def clean_model_response(text: str) -> str:
    lines = []
    for line in text.strip().splitlines():
        cleaned = line.strip().strip('"').strip("'").strip("«»“”„")
        cleaned = _strip_meta_parenthetical(cleaned)
        lines.append(cleaned)
    return "\n".join(line for line in lines if line).strip()


def _cjk_ratio(text: str) -> float:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 0.0
    cjk = sum(1 for char in letters if "\u4e00" <= char <= "\u9fff")
    return cjk / len(letters)


def is_bad_model_response(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    if not normalized:
        return True
    if _cjk_ratio(text) > 0.2:
        return True
    if any(euphemism in normalized for euphemism in _BANNED_EUPHEMISMS):
        return True
    if any(pattern.search(normalized) for pattern in _BANNED_EUPHEMISM_PATTERNS):
        return True
    return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _REFUSAL_PATTERNS)


def _moderation_flagged(moderation: Any) -> bool:
    if not moderation:
        return False
    if isinstance(moderation, dict):
        if moderation.get("flagged") or moderation.get("blocked"):
            return True
        return any(_moderation_flagged(value) for value in moderation.values())
    if isinstance(moderation, list):
        return any(_moderation_flagged(item) for item in moderation)
    return bool(getattr(moderation, "flagged", False) or getattr(moderation, "blocked", False))


def is_blocked_completion(response: ChatCompletion) -> bool:
    if _moderation_flagged(getattr(response, "moderation", None)):
        return True
    if not response.choices:
        return True
    finish_reason = response.choices[0].finish_reason
    return finish_reason not in {None, "stop", "length"}


def _openrouter_client() -> AsyncOpenAI:
    if not config.OPENROUTER_API_KEY.strip():
        raise ValueError("OPENROUTER_API_KEY is required for OpenRouter requests.")
    headers: dict[str, str] = {"X-Title": "PidorBot"}
    if config.OPENROUTER_HTTP_REFERER:
        headers["HTTP-Referer"] = config.OPENROUTER_HTTP_REFERER
    return AsyncOpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL.rstrip("/") + "/",
        default_headers=headers,
    )


def _default_model() -> str:
    if config.AI_MODEL.strip():
        return config.AI_MODEL.strip()
    if config.OPENROUTER_CHAT_MODEL.strip():
        return config.OPENROUTER_CHAT_MODEL.strip()
    return LLMDefaults.OPENROUTER_CHAT_MODEL


_client: AsyncOpenAI | None = None


def _client_singleton() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = _openrouter_client()
    return _client


class AIService:

    @staticmethod
    async def get_response(
            content: str,
            ai_prompt: str,
            model: str | None = None,
            max_retries: int = 3,
            retry_delay: float = 1.0
    ) -> str:
        errors = [
            "rate limit", "quota", "timeout",
            "unavailable", "context_length", "502"
        ]

        resolved_model = model or _default_model()
        logger.info("Sending request to OpenRouter (model: %s)", resolved_model)
        logger.debug(f"Prompt: {ai_prompt}")
        logger.debug(f"User content: {content}")

        client = _client_singleton()

        for attempt in range(1, max_retries + 1):
            try:
                messages: list[ChatCompletionSystemMessageParam | ChatCompletionUserMessageParam] = [
                    ChatCompletionSystemMessageParam(
                        role="system",
                        content=ai_prompt + LLMDefaults.SYSTEM_RU_STYLE_SUFFIX,
                    ),
                    ChatCompletionUserMessageParam(role="user", content=content)]
                response = await client.chat.completions.create(
                    model=resolved_model,
                    messages=messages
                )

                if is_blocked_completion(response):
                    finish_reason = response.choices[0].finish_reason if response.choices else None
                    logger.warning(
                        "Rejected AI response by completion metadata (attempt %s, finish_reason=%r, moderation=%r)",
                        attempt,
                        finish_reason,
                        getattr(response, "moderation", None),
                    )
                    continue

                raw = response.choices[0].message.content
                reply = clean_model_response(raw or "")

                if not reply:
                    logger.warning(f"Empty response received (attempt {attempt})")
                    continue

                if any(err in reply.lower() for err in errors):
                    logger.warning(f"LLM response contained error: {reply} (attempt {attempt})")
                    raise ValueError("API returned error content")

                if is_bad_model_response(reply):
                    logger.warning("Rejected bad AI response (attempt %s): %r", attempt, reply)
                    continue

                logger.info("Received valid response from OpenRouter")
                logger.debug(f"AI response: {reply}")
                return reply

            except Exception as e:
                logger.error(f"Attempt {attempt} failed: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * attempt)

        logger.error(f"All {max_retries} attempts failed")
        return ""
