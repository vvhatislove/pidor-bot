import asyncio

from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from openai import AsyncOpenAI
from config.config import config
from logger import setup_logger

logger = setup_logger(__name__)

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)  # 👈 Новый способ



class AI:

    @staticmethod
    async def get_response(
            content: str,
            ai_prompt: str,
            model: str = "gpt-4o-mini",
            max_retries: int = 3,
            retry_delay: float = 1.0
    ) -> str:
        errors = [
            "rate limit", "quota", "timeout",
            "unavailable", "context_length", "502"
        ]

        logger.info(f"Sending request to OpenAI (model: {model})")
        logger.debug(f"Prompt: {ai_prompt}")
        logger.debug(f"User content: {content}")

        for attempt in range(1, max_retries + 1):
            try:
                messages: list[ChatCompletionSystemMessageParam | ChatCompletionUserMessageParam] = [
                    ChatCompletionSystemMessageParam(role="system", content=ai_prompt),
                    ChatCompletionUserMessageParam(role="user", content=content)]
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages
                )

                reply = response.choices[0].message.content.strip()

                if not reply:
                    logger.warning(f"Empty response received (attempt {attempt})")
                    continue

                if any(err in reply.lower() for err in errors):
                    logger.warning(f"OpenAI response contained error: {reply} (attempt {attempt})")
                    raise ValueError("API returned error content")

                logger.info("Received valid response from OpenAI")
                logger.debug(f"AI response: {reply}")
                return reply

            except Exception as e:
                logger.error(f"Attempt {attempt} failed: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * attempt)

        logger.error(f"All {max_retries} attempts failed")
        return ""
