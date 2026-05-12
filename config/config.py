from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, model_validator
from pydantic_settings import BaseSettings

from logger import setup_logger

logger = setup_logger(__name__)


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_ID: int
    DATABASE_URL: str
    BOT_NAME: str
    OPENAI_API_KEY: str
    TIMEZONE: str

    # LLM: OpenAI directly or OpenRouter (OpenAI-compatible API, many low-refusal / RP models).
    AI_PROVIDER: Literal["openai", "openrouter"] = Field(
        default="openai",
        description='Use "openrouter" with a key from https://openrouter.ai/keys',
    )
    AI_MODEL: str = Field(
        default="",
        description="Override model id; if empty, defaults from config.constants.LLMDefaults",
    )
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_HTTP_REFERER: str | None = Field(
        default=None,
        description="Optional site URL for OpenRouter rankings (HTTP-Referer header)",
    )

    class Config:
        env_file = Path(__file__).parent.parent / '.env'
        env_file_encoding = 'utf-8'

    @model_validator(mode="after")
    def _ai_router_key(self) -> "Settings":
        if self.AI_PROVIDER == "openrouter":
            if not (self.OPENROUTER_API_KEY or self.OPENAI_API_KEY):
                raise ValueError(
                    "AI_PROVIDER=openrouter requires OPENROUTER_API_KEY or OPENAI_API_KEY (use one of them for the OpenRouter secret)."
                )
        return self


try:
    config = Settings()
    logger.info("Configuration loaded")
except ValidationError as e:
    logger.error("Error while loading configuration")
    logger.error(e.json())
    raise SystemExit("Невозможно продолжить без корректного .env файла.")
