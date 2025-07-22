import asyncio

from aiogram import Bot, Dispatcher

from config.config import config
from database import init_db
from handlers.admin import distribution
from handlers.user import (duel, common, update_data, registration,
                           triggers, pidor, stats, achievements,
                           balance, slots)
from logger import setup_logger
from middlewares.db_middleware import DbSessionMiddleware

logger = setup_logger(__name__)


async def main():
    logger.info("Starting bot")
    await init_db()
    logger.info("Database initialized")
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    dp.update.middleware(DbSessionMiddleware())

    for router in [
        # user
        common.router,
        registration.router,
        duel.router,
        update_data.router,
        pidor.router,
        stats.router,
        achievements.router,
        balance.router,
        slots.router,
        # admin
        distribution.router,

        triggers.router,  # Ensure triggers.router is last
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
