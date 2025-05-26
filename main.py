import asyncio
from aiogram import Bot, Dispatcher
from config.config import config
from database import init_db
from middlewares.db_middleware import DbSessionMiddleware
from handlers import common, admin, game, registration, triggers


async def main():
    await init_db()

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    # Подключаем middleware
    dp.update.middleware(DbSessionMiddleware())

    # Регистрируем роутеры
    for router in [
        common.router,
        # admin.router,
        game.router,
        registration.router,
        triggers.router
    ]:
        dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())