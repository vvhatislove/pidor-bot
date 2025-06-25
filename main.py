import asyncio
from aiogram import Bot, Dispatcher
from config.config import config
from database import init_db
from middlewares.db_middleware import DbSessionMiddleware
from handlers import common, admin, game, registration, triggers, duel
from logger import setup_logger

logger = setup_logger(__name__)


async def main():
    logger.info("Starting bot")
    await init_db()
    logger.info("Database initialized")
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
        duel.router,
        triggers.router,

    ]:
        dp.include_router(router)
    logger.info("Routers registered")
    await dp.start_polling(bot)
    logger.info("Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")