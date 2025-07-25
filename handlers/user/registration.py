from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database.CRUD.chat_crud import ChatCRUD
from database.CRUD.user_crud import UserCRUD
from sqlalchemy.ext.asyncio import AsyncSession
from config.constants import CommandText
from logger import setup_logger

logger = setup_logger(__name__)

router = Router()



@router.message(Command("reg"))
async def register_user(message: Message, session: AsyncSession):
    logger.info(f"/reg called by user {message.from_user.id} in chat {message.chat.id}")

    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        logger.info("Registration rejected: private chat")
        return

    user = await UserCRUD.get_user_by_telegram_id(session, message.from_user.id, message.chat.id)
    if user:
        await message.answer("Вы уже зарегистрировались 🤡")
        logger.info("User is already registered")
        return

    chat = await ChatCRUD.get_chat(session, message.chat.id)
    if chat is None:
        chat = await ChatCRUD.create_chat(
            session=session,
            chat_telegram_id=message.chat.id,
            title=message.chat.title
        )
        logger.info(f"Chat {message.chat.id} created")

    await UserCRUD.create_user(
        session=session,
        telegram_id=message.from_user.id,
        chat_telegram_id=chat.telegram_chat_id,
        first_name=message.from_user.first_name,
        username=message.from_user.username if message.from_user.username else ""
    )
    logger.info(f"User {message.from_user.id} registered successfully")
    await message.answer("Вы успешно зарегистрировались 🌈")


@router.message(Command("unreg"))
async def unregister_user(message: Message, session: AsyncSession):
    logger.info(f"/unreg called by user {message.from_user.id} in chat {message.chat.id}")

    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        logger.info("Unregistration rejected: private chat")
        return

    user = await UserCRUD.get_user_by_telegram_id(session, message.from_user.id, message.chat.id)
    if not user:
        await message.answer("Вы и так не зарегистрированы 🤡")
        logger.info("User is not registered")
        return

    await UserCRUD.delete_user(session, user)
    logger.info(f"User {message.from_user.id} unregistered")
    await message.answer(
        "Вы отменили регистрацию 🙅‍♂️ и проебали всю статистику\n"
        "А что поделать, такова жизнь 🤷‍♂️"
    )


@router.message(Command("showreg"))
async def show_registered_users(message: Message, session: AsyncSession):
    logger.info(f"/showreg called in chat {message.chat.id}")

    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        logger.info("Show registration rejected: private chat")
        return

    users = await UserCRUD.get_chat_users(session, message.chat.id)
    if not users:
        await message.answer(
            "Нет зарегистрированных пользователей 🙇‍♂️\n"
            "Чтобы зарегистрироваться напишите /reg"
        )
        logger.info("No registered users found")
        return

    users_list = "\n".join(
        f"{i}. 👉 {u.username or u.first_name}" for i, u in enumerate(users, 1)
    )
    logger.info(f"Registered users in chat {message.chat.id}: {len(users)}")
    await message.answer(f"📋 Зарегистрированные участники:\n{users_list}")
