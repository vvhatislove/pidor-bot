from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database.crud import UserCRUD, ChatCRUD
from sqlalchemy.ext.asyncio import AsyncSession
from config.constants import CommandText

router = Router()


@router.message(Command("reg"))
async def register_user(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return

    user = await UserCRUD.get_user(session, message.from_user.id, message.chat.id)
    if user:
        await message.answer("Вы уже зарегистрировались 🤡")
        return

    chat = await ChatCRUD.get_chat(session, message.chat.id)

    if chat is None:
        chat = await ChatCRUD.create_chat(
            session=session,
            chat_telegram_id=message.chat.id,
            title=message.chat.title
        )

    new_user = await UserCRUD.create_user(
        session=session,
        telegram_id=message.from_user.id,
        chat_telegram_id=chat.chat_id,
        first_name=message.from_user.first_name,
        username=message.from_user.username
    )

    await message.answer("Вы успешно зарегистрировались 🌈")


@router.message(Command("unreg"))
async def unregister_user(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return

    user = await UserCRUD.get_user(session, message.from_user.id, message.chat.id)

    if not user:
        await message.answer("Вы и так не зарегистрированы 🤡")
        return

    await UserCRUD.delete_user(session, user)
    await message.answer(
        "Вы отменили регистрацию 🙅‍♂️ и проебали всю статистику\n"
        "А что поделать, такова жизнь 🤷‍♂️"
    )


@router.message(Command("showreg"))
async def show_registered_users(message: Message, session: AsyncSession):
    if message.chat.type == "private":
        await message.answer(CommandText.WRONG_CHAT)
        return

    users = await UserCRUD.get_chat_users(session, message.chat.id)

    if not users:
        await message.answer(
            "Нет зарегистрированных пользователей 🙇‍♂️\n"
            "Чтобы зарегистрироваться напишите /reg"
        )
        return

    users_list = "\n".join(
        f"{i}. 👉 {u.username or u.first_name}"
        for i, u in enumerate(users, 1)
    )

    await message.answer(f"📋 Зарегистрированные участники:\n{users_list}")
