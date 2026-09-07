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
from bot.scheduler import schedule_monitor_loop, lesson_alert_loop
from bot.utils import get_cached_schedule, reload_cached_schedule, set_subscribers_cache
from database.db import init_db, close_db, get_active_subscribers_db, is_db_connected, save_schedule_db

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
    Warms up in-memory cache.
    """
    if not SCHEDULE_FILE.exists() or not load_schedule():
        logger.info("Schedule not found locally. Fetching initial schedule from Google Drive...")
        meta = await fetch_latest_schedule_meta()
        if meta:
            await download_and_parse_schedule(meta["file_id"])
            save_schedule_meta(meta)
            reload_cached_schedule()
            logger.info("Initial schedule successfully loaded and cached!")
        else:
            logger.warning("Could not fetch initial schedule meta from Google Drive.")
    else:
        get_cached_schedule()

    if is_db_connected():
        sched = get_cached_schedule()
        if sched:
            await save_schedule_db(GROUP_NAME, sched.get("file_id", ""), sched.get("updated_at", ""), sched)

async def main():
    # Initialize MySQL Database
    db_ok = await init_db()
    if db_ok:
        active_subs = await get_active_subscribers_db()
        set_subscribers_cache(active_subs)

    # Initial data check
    await ensure_initial_schedule()

    # CLI test argument support
    if len(sys.argv) > 1 and sys.argv[1] in ["--parse-only", "--test"]:
        logger.info("CLI test completed successfully.")
        await close_db()
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
        await close_db()
        sys.exit(1)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(router)

    # Launch background tasks: schedule monitor and lesson alerts
    monitor_task = asyncio.create_task(schedule_monitor_loop(bot))
    alert_task = asyncio.create_task(lesson_alert_loop(bot))

    logger.info(f"Telegram-бот для групи {GROUP_NAME} запущено!")
    try:
        await dp.start_polling(bot)
    finally:
        monitor_task.cancel()
        alert_task.cancel()
        await asyncio.gather(monitor_task, alert_task, return_exceptions=True)
        await bot.session.close()
        await close_db()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот зупинено.")
