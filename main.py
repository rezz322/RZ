import sys
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, GROUP_NAME, SCHEDULE_FILE
from parser.monitor import fetch_latest_schedule_meta, save_schedule_meta
from parser.schedule_parser import download_and_parse_schedule, load_schedule
from bot.handlers import router
from bot.scheduler import schedule_monitor_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("main")

async def ensure_initial_schedule():
    """
    Checks if schedule is already parsed. If not, fetches from Google Drive.
    """
    if not SCHEDULE_FILE.exists() or not load_schedule():
        logger.info("Schedule not found locally. Fetching initial schedule from Google Drive...")
        meta = await fetch_latest_schedule_meta()
        if meta:
            await download_and_parse_schedule(meta["file_id"])
            save_schedule_meta(meta)
            logger.info("Initial schedule successfully loaded and cached!")
        else:
            logger.warning("Could not fetch initial schedule meta from Google Drive.")

async def main():
    # Initial data check
    await ensure_initial_schedule()

    # CLI test argument support
    if len(sys.argv) > 1 and sys.argv[1] in ["--parse-only", "--test"]:
        logger.info("CLI test completed successfully.")
        return

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error(
            "\n"
            "===============================================================\n"
            "ПОМИЛКА: Не вказано BOT_TOKEN!\n"
            "1. Отримайте токен у @BotFather в Telegram.\n"
            "2. Відкрийте файл .env або створіть його за зразком .env.example.\n"
            "3. Вкажіть BOT_TOKEN=ваш_токен_тут\n"
            "===============================================================\n"
        )
        sys.exit(1)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(router)

    # Launch background schedule monitor
    monitor_task = asyncio.create_task(schedule_monitor_loop(bot))

    logger.info(f"Telegram-бот для групи {GROUP_NAME} запущено!")
    try:
        await dp.start_polling(bot)
    finally:
        monitor_task.cancel()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот зупинено.")
