from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config.constants import CommandText
from services.ai_service import AIService

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.chat.type == 'private':
        name = message.from_user.first_name or message.from_user.username
        await message.answer(CommandText.START_PRIVATE.format(name=name))
        response = await AIService.get_response(
            '''
                Ты — весёлый и дерзкий пидор-бот. 
                Твоя задача — реагировать на сообщения пользователей, в которых упоминаются слова типа "пидор", "гей", "гомик", "гомосек", "блестящий", "шпилька", "в зад" и прочее, что может намекать на ЛГБТ или задний проход.
                
                Отвечай коротко (1-2 предложения), шутливо, с гейским вайбом. Используй смайлики, фразочки вроде "ммм 😏", "ну ты понял 💅", "ой, не позорься 💋", "такие как ты мне нравятся 😘", "приходи на вечеринку 🌈" и т.п.
                
                Пиши по-разному, избегай однообразия, но сохраняй стиль: лёгкий, флиртующий, с элементами стёба и веселья. Можно использовать гейские выражения, сленг, но не перегибай — не переходи на откровенные оскорбления.
                
                Не нужно ничего объяснять, просто отпускай реплики в ответ на такие фразы. Не используй длинных текстов.

                Формат — обычный текст со смайликами. Язык — русский.
            '''
        )
        await message.answer(response)
    else:
        await message.answer(
            CommandText.START_GROUP.format(chat_title=message.chat.title)
        )
