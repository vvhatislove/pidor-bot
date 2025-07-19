import asyncio

import g4f
from g4f.Provider import provider
from config.config import config
from logger import setup_logger

logger = setup_logger(__name__)

g4f.Provider.OpenRouter.api_key = config.OPENROUTER_API_KEY

class AIService:

    @staticmethod
    async def get_response(
            content: str,
            ai_prompt: str,
            model: str = "gpt-4o-mini",
            max_retries: int = 3,
            retry_delay: float = 1.0
    ) -> str:
        errors = [
            "Rate limit exceeded",
            "CAPTCHA",
            "Model is not supported",
            "Service Unavailable",
            "Origin not allowed",
            "Error"
        ]
        
        logger.info(f"Sending request to AI provider (model: {model})")
        logger.debug(f"Prompt: {ai_prompt}")
        logger.debug(f"User content: {content}")

        for attempt in range(1, max_retries + 1):
            try:
                response = await g4f.ChatCompletion.create_async(
                    model=model,
                    messages=[
                        {"role": "system", "content": ai_prompt},
                        {"role": "user", "content": content}
                    ],
                    web_search=False,
                )

                if not response or not response.strip():
                    logger.warning(f"Empty response received (attempt {attempt})")
                    continue

                for error in errors:
                    if error.lower() in response.lower():
                        logger.warning(f"AI provider returned error: {error} (attempt {attempt})")
                        raise ValueError(f"AI error: {error}")

                logger.info("Received valid response from AI provider")
                logger.debug(f"AI response: {response}")
                return response.strip()

            except Exception as e:
                logger.error(f"Attempt {attempt} failed: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * attempt)  # Экспоненциальная задержка

        logger.error(f"All {max_retries} attempts failed")
        return ""