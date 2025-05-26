from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from config.config import config
from config.constants import CommandText, AIPromt, Commands
from services.ai_service import AIService

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.chat.type == 'private':
        name = message.from_user.first_name or message.from_user.username
        await message.answer(CommandText.START_PRIVATE.format(name=name))
    else:
        await message.answer(
            CommandText.START_GROUP.format(chat_title=message.chat.title)
        )

@router.message(Command("help"))
async def help_start(message: Message):
    help_message = "Доступные команды: \n\n"
    if config.ADMIN_ID == message.from_user.id and message.chat.type == 'private':
        for command, description in Commands.PUBLIC_GROUP:
            help_message += f"/{command} - {description}\n"
        help_message += "\n\n"
        help_message += "Доступные административные команды: \n\n"
        for command, description in Commands.ADMIN:
            help_message += f"/{command} - {description}\n"
    else:
        bot_name = "" if message.chat.type == 'private' else config.BOT_NAME
        for command, description in Commands.PUBLIC_GROUP:
            help_message += f"/{command}{bot_name} - {description}\n"
    await message.answer(help_message)