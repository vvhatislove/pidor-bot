from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command

from config.config import config
from config.constants import CommandText, Commands
from logger import setup_logger

logger = setup_logger(__name__)

router = Router()


def _format_help_command(command: str, bot_name: str) -> str:
    parts = command.split(maxsplit=1)
    suffix = f" {parts[1]}" if len(parts) > 1 else ""
    return f"/{parts[0]}{bot_name}{suffix}"


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
    bot_name = "" if message.chat.type == 'private' else config.BOT_NAME
    logger.debug(f"Help menu generated for user {message.from_user.id}")
    for command, description in Commands.PUBLIC_GROUP:
        help_message += f"{_format_help_command(command, bot_name)} - {description}\n"

    if config.ADMIN_ID == message.from_user.id:
        help_message += "\n\n"
        if message.chat.type == 'private':
            admin_commands = Commands.ADMIN_PRIVATE
            help_message += "Административные команды в ЛС: \n\n"
        else:
            admin_commands = Commands.ADMIN_GROUP
            help_message += "Административные команды в этом чате: \n\n"
        for command, description in admin_commands:
            help_message += f"{_format_help_command(command, bot_name)} - {description}\n"
    await message.answer(help_message)

@router.message(Command("test"))
async def cmd_test(message: Message):
    logger.info(f"/test requested by user {message.from_user.id} in chat {message.chat.id}")
    if message.chat.type == "private":
        logger.info("Rejected /stats: private chat")
        await message.answer(CommandText.WRONG_CHAT)
        return
    await message.answer(f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>', parse_mode=ParseMode.HTML)
