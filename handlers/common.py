from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config.constants import CommandText, AIPromt
from services.ai_service import AIService

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    print(f"START command received from {message.from_user.id}")
    if message.chat.type == 'private':
        name = message.from_user.first_name or message.from_user.username
        await message.answer(CommandText.START_PRIVATE.format(name=name))
    else:
        await message.answer(
            CommandText.START_GROUP.format(chat_title=message.chat.title)
        )
