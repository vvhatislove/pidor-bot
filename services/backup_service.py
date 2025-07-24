import os
import time
from datetime import datetime
from zipfile import ZipFile

from aiogram import Bot
from aiogram.types import FSInputFile

from config.config import config
from logger import setup_logger
from services.utils import wait_until

logger = setup_logger(__name__)


def clean_old_backups(backup_dir: str = "./backups", days: int = 2):
    now = time.time()
    removed = []
    logger.info(f"Checking for backups older than {days} days...")
    for filename in os.listdir(backup_dir):
        path = os.path.join(backup_dir, filename)
        if os.path.isfile(path):
            file_age = now - os.path.getmtime(path)
            if file_age > days * 86400:
                os.remove(path)
                removed.append(filename)
                logger.info(f"🗑️ Deleted old backup: {filename}")
    if not removed:
        logger.info("No outdated backups found")
    return removed


def create_backup_zip(
        db_path: str = "./database/storage/database.db",
        env_path: str = ".env",
        backup_dir: str = "./backups"
) -> str:
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    zip_name = f"backup_{timestamp}.zip"
    zip_path = os.path.join(backup_dir, zip_name)

    logger.info("Creating backup archive...")
    with ZipFile(zip_path, 'w') as zipf:
        if os.path.exists(db_path):
            zipf.write(db_path, arcname=os.path.basename(db_path))
            logger.info(f"Added DB file: {db_path}")
        else:
            logger.warning(f"DB file not found: {db_path}")
        if os.path.exists(env_path):
            zipf.write(env_path, arcname=os.path.basename(env_path))
            logger.info(f"Added .env file")
        else:
            logger.warning(".env file not found")

    logger.info(f"Backup archive created: {zip_path}")
    return zip_path


async def backup_scheduler(bot: Bot):
    logger.info("Backup scheduler started")
    while True:
        await wait_until(14, 33)
        logger.info("Time to run backup")
        backup_path = create_backup_zip()
        await send_backup_to_telegram(bot, backup_path)
        clean_old_backups()


async def send_backup_to_telegram(bot: Bot, backup_path: str):
    try:
        file = FSInputFile(backup_path)
        await bot.send_document(config.ADMIN_ID, document=file, caption="🛡️ Backup file")
        logger.info(f"Backup sent to admin ({config.ADMIN_ID})")
    except Exception as e:
        logger.error(f"Failed to send backup: {e}")
