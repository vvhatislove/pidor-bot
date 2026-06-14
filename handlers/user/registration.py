from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database.repositories.chat_repository import ChatRepository
from database.repositories.user_repository import UserRepository
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

    user = await UserRepository.get_user_by_telegram_id(session, message.from_user.id, message.chat.id)
    if user:
        if user.is_active:
            await message.answer("Вы уже участвуете в розыгрыше пидора дня 🤡")
            logger.info("User is already active")
            return
        await UserRepository.activate_user(
            session=session,
            user=user,
            first_name=message.from_user.first_name,
            username=message.from_user.username if message.from_user.username else "",
        )
        await message.answer("Вы снова участвуете в розыгрыше пидора дня 🌈")
        logger.info("User reactivated")
        return

    chat = await ChatRepository.get_chat(session, message.chat.id)
    if chat is None:
        chat = await ChatRepository.create_chat(
            session=session,
            chat_telegram_id=message.chat.id,
            title=message.chat.title
        )
        logger.info(f"Chat {message.chat.id} created")

    await UserRepository.create_user(
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

    user = await UserRepository.get_user_by_telegram_id(session, message.from_user.id, message.chat.id)
    if not user:
        await message.answer("Вы и так не зарегистрированы 🤡")
        logger.info("User is not registered")
        return

    if not user.is_active:
        await message.answer("Вы уже не участвуете в розыгрыше пидора дня 🤡")
        logger.info("User is already inactive")
        return

    await UserRepository.deactivate_user(session, user)
    logger.info(f"User {message.from_user.id} unregistered")
    await message.answer("Вы больше не участвуете в розыгрыше пидора дня 🙅‍♂️")


@router.message(Command("showreg"))
async def show_registered_users(message: Message, session: AsyncSession):
    logger.info(f"/showreg called in chat {message.chat.id}")

    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        logger.info("Show registration rejected: private chat")
        return

    users = await UserRepository.get_chat_users(session, message.chat.id)
    if not users:
        await message.answer(
            "Нет участников розыгрыша пидора дня 🙇‍♂️\n"
            "Чтобы зарегистрироваться напишите /reg"
        )
        logger.info("No registered users found")
        return

    users_list = "\n".join(
        f"{i}. 👉 {u.username or u.first_name}" for i, u in enumerate(users, 1)
    )
    logger.info(f"Active users in chat {message.chat.id}: {len(users)}")
    await message.answer(f"📋 Участники розыгрыша пидора дня:\n{users_list}")
