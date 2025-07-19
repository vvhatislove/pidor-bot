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
        short_event = f"{type(event).__name__}"
        if hasattr(event, "from_user"):
            short_event += f" from {event.from_user.id}"
        elif hasattr(event, "message") and hasattr(event.message, "from_user"):
            short_event += f" from {event.message.from_user.id}"
        logger.info(f"DB session opened for event: {short_event}")
        async with async_session() as session:
            data["session"] = session
            result = await handler(event, data)
            logger.info("Database session closed successfully")
            return result