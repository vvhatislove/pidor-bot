from aiogram import BaseMiddleware
from typing import Callable, Awaitable, Any, Dict
from aiogram.types import TelegramObject
from database import async_session
from logger import setup_logger

logger = setup_logger(__name__)

class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        logger.info(f"Opening database session for event: {event}")
        async with async_session() as session:
            data["session"] = session
            result = await handler(event, data)
            logger.info("Database session closed successfully")
            return result