import asyncio

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from config.config import config
from config.constants import LLMDefaults
from logger import setup_logger

logger = setup_logger(__name__)


def _openai_client() -> AsyncOpenAI:
    if config.AI_PROVIDER == "openrouter":
        key = config.OPENROUTER_API_KEY or config.OPENAI_API_KEY
        headers: dict[str, str] = {"X-Title": "PidorBot"}
        if config.OPENROUTER_HTTP_REFERER:
            headers["HTTP-Referer"] = config.OPENROUTER_HTTP_REFERER
        return AsyncOpenAI(
            api_key=key,
            base_url=config.OPENROUTER_BASE_URL.rstrip("/") + "/",
            default_headers=headers,
        )
    return AsyncOpenAI(api_key=config.OPENAI_API_KEY)


def _default_model() -> str:
    if config.AI_MODEL.strip():
        return config.AI_MODEL.strip()
    if config.AI_PROVIDER == "openrouter":
        return LLMDefaults.OPENROUTER_CHAT_MODEL
    return LLMDefaults.OPENAI_CHAT_MODEL


_client: AsyncOpenAI | None = None


def _client_singleton() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = _openai_client()
    return _client


class AI:

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
        provider_label = "OpenRouter" if config.AI_PROVIDER == "openrouter" else "OpenAI"
        logger.info("Sending request to %s (model: %s)", provider_label, resolved_model)
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

                raw = response.choices[0].message.content
                reply = (raw or "").strip()

                if not reply:
                    logger.warning(f"Empty response received (attempt {attempt})")
                    continue

                if any(err in reply.lower() for err in errors):
                    logger.warning(f"LLM response contained error: {reply} (attempt {attempt})")
                    raise ValueError("API returned error content")

                logger.info("Received valid response from %s", provider_label)
                logger.debug(f"AI response: {reply}")
                return reply

            except Exception as e:
                logger.error(f"Attempt {attempt} failed: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * attempt)

        logger.error(f"All {max_retries} attempts failed")
        return ""
