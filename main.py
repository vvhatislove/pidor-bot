import asyncio
import os

from aiogram import Bot, Dispatcher

from config.config import config
from database import init_db
from handlers.admin import distribution
from handlers.user import (duel, common, update_data, registration,
                           triggers, pidor, stats, achievements,
                           balance, slots, profile, auto_pidor)
from logger import setup_logger
from middlewares.db_middleware import DbSessionMiddleware
from services.auto_pidor_service import auto_pidor_scheduler
from services.backup_service import backup_scheduler

logger = setup_logger(__name__)


async def main():
    logger.info("Starting bot")
    database_dir = "./database/storage"
    os.makedirs(database_dir, exist_ok=True)
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
        profile.router,
        auto_pidor.router,
        # admin
        distribution.router,

        triggers.router,  # Ensure triggers.router is last
    ]:
        dp.include_router(router)
    asyncio.create_task(auto_pidor_scheduler(bot))
    asyncio.create_task(backup_scheduler(bot))
    logger.info("Routers registered")
    await dp.start_polling(bot)
    logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
