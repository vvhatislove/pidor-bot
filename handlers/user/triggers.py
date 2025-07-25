from datetime import datetime, timezone

from aiogram import Router
from aiogram.types import Message

from config.constants import GameText, AIPromt
from logger import setup_logger
from handlers.utils.AI import AI

logger = setup_logger(__name__)
router = Router()


@router.message()
async def trigger_handler(message: Message):
    if message.chat.type == "private":
        return
    message_ttl_seconds = 60
    # Проверка на "устаревшее" сообщение
    message_time = datetime.fromtimestamp(message.date.timestamp(), tz=timezone.utc)
    now = datetime.now(timezone.utc)
    delta_seconds = (now - message_time).total_seconds()
    if delta_seconds > message_ttl_seconds:
        return  # старое сообщение — игнорируем

    if message.text:
        text = message.text
        if not isinstance(text, str):
            return
        try:
            text = str(text)
        except Exception as e:
            logger.error(f"Error in trigger_handler: {e}")
            return
        text = text.lower()
        logger.info("TRIGGER: %s", text)
        for trigger in GameText.TRIGGERS:
            if trigger in text:
                trigger_message = await AI.get_response(text, AIPromt.PIDOR_TRIGGERS_PROMPT)
                if trigger_message:
                    logger.info("Sent trigger answer")
                    await message.reply(trigger_message)
                break
