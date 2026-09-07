import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramBadRequest

from config import (
    CHECK_INTERVAL_SECONDS,
    ALERT_MINUTES_BEFORE,
    GROUP_NAME
)
from parser.monitor import (
    fetch_latest_schedule_meta,
    has_schedule_changed,
    save_schedule_meta
)
from parser.schedule_parser import (
    get_academic_week_info,
    filter_lessons_for_week,
    download_and_parse_schedule
)
from bot.templates import (
    format_lesson_alert_text,
    format_schedule_update_alert_text
)
from bot.utils import (
    get_cached_schedule,
    reload_cached_schedule,
    get_subscribers,
    unregister_subscriber
)

logger = logging.getLogger(__name__)

LESSON_TIMES = [
    {"pair": "1", "start": "08:00", "end": "09:35"},
    {"pair": "2", "start": "09:50", "end": "11:25"},
    {"pair": "3", "start": "11:40", "end": "13:15"},
    {"pair": "4", "start": "13:30", "end": "15:05"},
    {"pair": "5", "start": "15:20", "end": "16:55"}
]

async def broadcast_lesson_alert(bot: Bot, pair_num: str, time_info: dict, lessons: list[dict]):
    """
    Розсилає сповіщення про початок пари всім підписникам.
    """
    subscribers = get_subscribers()
    if not subscribers:
        return

    text = format_lesson_alert_text(pair_num, time_info, lessons, ALERT_MINUTES_BEFORE)
    logger.info(f"Broadcasting lesson alert for pair {pair_num} to {len(subscribers)} subscribers...")

    for chat_id in subscribers:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            await asyncio.sleep(0.04)
        except TelegramForbiddenError:
            logger.info(f"User {chat_id} blocked the bot, removing from subscribers.")
            unregister_subscriber(chat_id)
        except TelegramRetryAfter as e:
            logger.warning(f"Telegram rate limit hit, waiting {e.retry_after}s...")
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True)
            except Exception:
                pass
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower() or "deactivated" in str(e).lower():
                unregister_subscriber(chat_id)
            else:
                logger.warning(f"BadRequest sending alert to {chat_id}: {e}")
        except Exception as e:
            logger.warning(f"Failed to send lesson alert to chat {chat_id}: {e}")

async def lesson_alert_loop(bot: Bot):
    """
    Фоновий цикл перевірки початку пар та надсилання нагадувань усім студентам за 10 хвилин.
    """
    logger.info(f"Starting lesson alert loop (alerts ~{ALERT_MINUTES_BEFORE}m before pair)...")
    sent_alerts = set()

    while True:
        try:
            await asyncio.sleep(30)
            now = datetime.now()
            today = now.date()
            today_str = today.strftime("%Y-%m-%d")

            # Очищуємо історію попередніх днів
            sent_alerts = {item for item in sent_alerts if item[0] == today_str}

            # Пропускаємо вихідні дні (субота = 5, неділя = 6)
            if today.weekday() >= 5:
                continue

            schedule = get_cached_schedule()
            if not schedule:
                continue

            week_info = get_academic_week_info(today)
            day_name = week_info["day_name"]
            day_pairs = schedule.get("days", {}).get(day_name, {})

            for item in LESSON_TIMES:
                pair_num = item["pair"]
                if (today_str, pair_num) in sent_alerts:
                    continue

                raw_lessons = day_pairs.get(pair_num, [])
                active_lessons = filter_lessons_for_week(
                    raw_lessons,
                    week_info["week_number"],
                    week_info["parity"]
                )
                if not active_lessons:
                    continue

                start_h, start_m = map(int, item["start"].split(":"))
                start_dt = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
                alert_dt = start_dt - timedelta(minutes=ALERT_MINUTES_BEFORE)

                if alert_dt <= now < start_dt:
                    logger.info(f"Triggering lesson alert for pair {pair_num} on {today_str}")
                    sent_alerts.add((today_str, pair_num))
                    await broadcast_lesson_alert(bot, pair_num, item, active_lessons)

        except asyncio.CancelledError:
            logger.info("Lesson alert loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in lesson alert loop: {e}", exc_info=True)
            await asyncio.sleep(10)

async def notify_schedule_update(bot: Bot, meta: dict):
    """
    Розсилає сповіщення про оновлення файлу розкладу на Google Drive (вимкнено).
    """
    return

async def schedule_monitor_loop(bot: Bot):
    """
    Періодичний моніторинг папки на Google Drive.
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
                reload_cached_schedule()
                # Сповіщення про оновлення розкладу вимкнено
        except asyncio.CancelledError:
            logger.info("Schedule monitor loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}", exc_info=True)
            await asyncio.sleep(60)
