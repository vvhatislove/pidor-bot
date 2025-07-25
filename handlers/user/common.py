from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command

from config.config import config
from config.constants import CommandText, Commands
from logger import setup_logger

logger = setup_logger(__name__)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.chat.type == 'private':
        name = message.from_user.first_name or message.from_user.username
        logger.info(f"User {message.from_user.id} ({name}) started the bot in private chat")
        await message.answer(CommandText.START_PRIVATE.format(name=name))
    else:
        logger.info(f"Bot started in group {message.chat.id} ({message.chat.title})")
        await message.answer(
            CommandText.START_GROUP.format(chat_title=message.chat.title)
        )

@router.message(Command("help"))
async def help_start(message: Message):
    logger.info(f"Help command requested by user {message.from_user.id} in chat {message.chat.id}")
    help_message = "Доступные команды: \n\n"
    if config.ADMIN_ID == message.from_user.id and message.chat.type == 'private':
        logger.debug(f"Admin help menu generated for user {message.from_user.id}")
        for command, description in Commands.PUBLIC_GROUP:
            help_message += f"/{command} - {description}\n"
        help_message += "\n\n"
        help_message += "Доступные административные команды: \n\n"
        for command, description in Commands.ADMIN:
            help_message += f"/{command} - {description}\n"
    else:
        bot_name = "" if message.chat.type == 'private' else config.BOT_NAME
        logger.debug(f"Regular help menu generated for user {message.from_user.id}")
        for command, description in Commands.PUBLIC_GROUP:
            help_message += f"/{command}{bot_name} - {description}\n"
    await message.answer(help_message)

@router.message(Command("test"))
async def cmd_test(message: Message):
    logger.info(f"/test requested by user {message.from_user.id} in chat {message.chat.id}")
    if message.chat.type == "private":
        logger.info("Rejected /stats: private chat")
        await message.answer(CommandText.WRONG_CHAT)
        return
    await message.answer(f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>', parse_mode=ParseMode.HTML)