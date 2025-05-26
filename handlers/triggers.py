from aiogram import Router, F
from aiogram.types import Message

from config.constants import CommandText, GameText, AIPromt
from services.ai_service import AIService

router = Router()

@router.message()
async def trigger_handler(message: Message):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return
    if message.text:
        text = message.text
        if not isinstance(text, str):
            return
        else:
            try:
                text = str(text)
            except Exception as e:
                print(f"Ошибка преобразования в строку: {e}")
                return
            for trigger in GameText.TRIGGERS:
                if trigger in text:
                    trigger_message = await AIService.get_response(text, AIPromt.PIDOR_TRIGGERS_PROMT)
                    await message.reply(trigger_message)
                    break  # чтобы не отвечать на несколько триггеров одновременно


