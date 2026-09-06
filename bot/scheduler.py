import asyncio
import json
import logging
from aiogram import Bot

from config import (
    CHECK_INTERVAL_SECONDS,
    SUBSCRIBERS_FILE,
    GROUP_NAME
)
from parser.monitor import (
    fetch_latest_schedule_meta,
    has_schedule_changed,
    save_schedule_meta
)
from parser.schedule_parser import download_and_parse_schedule

logger = logging.getLogger(__name__)

async def notify_subscribers(bot: Bot, meta: dict):
    """
    Broadcasts notification to all registered users when schedule is updated.
    """
    if not SUBSCRIBERS_FILE.exists():
        return
        
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            subscribers = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read subscribers: {e}")
        return
        
    msg = (
        f"🔔 <b>УВАГА! РОЗКЛАД ОНОВЛЕНО НА САЙТІ ФАКУЛЬТЕТУ!</b>\n\n"
        f"• Документ: <code>{meta.get('title', 'Новий розклад')}</code>\n"
        f"• Дата модифікації: <b>{meta.get('last_modified', 'щойно')}</b>\n"
        f"• Група: <b>{GROUP_NAME}</b>\n\n"
        f"Бот уже завантажив нову версію розкладу. Натисніть <b>📅 Сьогодні</b> або <b>🗓 Розклад</b>, щоб переглянути актуальні заняття!"
    )
    
    for chat_id in subscribers:
        try:
            await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
            await asyncio.sleep(0.05)  # rate limit precaution
        except Exception as e:
            logger.warning(f"Failed to notify chat {chat_id}: {e}")

async def schedule_monitor_loop(bot: Bot):
    """
    Periodic background loop that monitors Google Drive folder.
    """
    logger.info(f"Starting schedule monitor loop (interval: {CHECK_INTERVAL_SECONDS}s)...")
    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
            meta = await fetch_latest_schedule_meta()
            if meta and has_schedule_changed(meta):
                logger.info(f"Schedule update detected: {meta['title']}")
                await download_and_parse_schedule(meta["file_id"])
                save_schedule_meta(meta)
                await notify_subscribers(bot, meta)
        except asyncio.CancelledError:
            logger.info("Schedule monitor loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}", exc_info=True)
            await asyncio.sleep(60)  # retry wait on error
