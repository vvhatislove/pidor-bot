from pathlib import Path

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from logger import setup_logger

logger = setup_logger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BOT_TOKEN: str
    ADMIN_ID: int
    DATABASE_URL: str
    BOT_NAME: str
    TIMEZONE: str

    OPENROUTER_API_KEY: str = ""
    AI_MODEL: str = Field(
        default="",
        description="OpenRouter model id; if empty, defaults from config.constants.LLMDefaults.OPENROUTER_CHAT_MODEL.",
    )
    OPENROUTER_CHAT_MODEL: str = Field(
        default="",
        description="Legacy OpenRouter model override; prefer AI_MODEL for new configs.",
    )
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_HTTP_REFERER: str | None = Field(
        default=None,
        description="Optional site URL for OpenRouter rankings (HTTP-Referer header)",
    )
    AI_BUFFER_TARGET_SIZE: int = 10
    AI_BUFFER_REFILL_INTERVAL_SECONDS: int = 30
    AI_BUFFER_GENERATION_CONCURRENCY: int = 2
    AI_BUFFER_STORAGE_PATH: str = "database/storage/ai_response_buffer.json"

try:
    config = Settings()
    logger.info("Configuration loaded")
except ValidationError as e:
    logger.error("Error while loading configuration")
    logger.error(e.json())
    raise SystemExit("Невозможно продолжить без корректного .env файла.")
