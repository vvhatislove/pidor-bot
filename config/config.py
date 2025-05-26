from pydantic import ValidationError
from pydantic_settings import BaseSettings
from pathlib import Path
from logger import setup_logger

logger = setup_logger(__name__)

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_ID: int
    DATABASE_URL: str
    OPENROUTER_API_KEY: str
    BOT_NAME: str

    class Config:
        env_file = Path(__file__).parent.parent / '.env'
        env_file_encoding = 'utf-8'


try:
    config = Settings()
    logger.info("Configuration loaded")
except ValidationError as e:
    logger.error("Error while loading configuration")
    logger.error(e.json())
    raise SystemExit("Невозможно продолжить без корректного .env файла.")
