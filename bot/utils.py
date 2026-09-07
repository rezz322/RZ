import json
import logging
from config import SUBSCRIBERS_FILE
from parser.schedule_parser import load_schedule

logger = logging.getLogger(__name__)

# Оперативний кеш розкладу в пам'яті (Singleton)
_SCHEDULE_CACHE: dict | None = None

def get_cached_schedule() -> dict | None:
    """
    Миттєво повертає розклад з оперативної пам'яті.
    Якщо пам'ять порожня — одноразово завантажує з schedule.json.
    """
    global _SCHEDULE_CACHE
    if _SCHEDULE_CACHE is None:
        _SCHEDULE_CACHE = load_schedule()
        if _SCHEDULE_CACHE:
            logger.info("Schedule successfully loaded into in-memory cache.")
    return _SCHEDULE_CACHE

def update_cached_schedule(schedule_data: dict) -> None:
    """
    Оновлює розклад у пам'яті.
    """
    global _SCHEDULE_CACHE
    _SCHEDULE_CACHE = schedule_data
    logger.info("In-memory schedule cache updated.")

def reload_cached_schedule() -> dict | None:
    """
    Примусово перезавантажує schedule.json у пам'ять.
    """
    global _SCHEDULE_CACHE
    _SCHEDULE_CACHE = load_schedule()
    logger.info("In-memory schedule cache reloaded from disk.")
    return _SCHEDULE_CACHE

# Оперативний кеш списку підписників у пам'яті
_SUBSCRIBERS_CACHE: set[int] | None = None

def get_subscribers() -> list[int]:
    """
    Повертає список зареєстрованих підписників бота (з кешу або диску).
    """
    global _SUBSCRIBERS_CACHE
    if _SUBSCRIBERS_CACHE is None:
        if not SUBSCRIBERS_FILE.exists():
            _SUBSCRIBERS_CACHE = set()
        else:
            try:
                with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                    _SUBSCRIBERS_CACHE = set(json.load(f))
            except Exception as e:
                logger.error(f"Failed to read subscribers from {SUBSCRIBERS_FILE}: {e}")
                _SUBSCRIBERS_CACHE = set()
    return list(_SUBSCRIBERS_CACHE)

def register_subscriber(chat_id: int) -> None:
    """
    Зберігає chat_id користувача. Якщо вже є в пам'яті — операція 0ms без читання диску.
    """
    global _SUBSCRIBERS_CACHE
    if _SUBSCRIBERS_CACHE is None:
        get_subscribers()
    if chat_id not in _SUBSCRIBERS_CACHE:
        _SUBSCRIBERS_CACHE.add(chat_id)
        try:
            with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
                json.dump(list(_SUBSCRIBERS_CACHE), f, indent=2)
            logger.info(f"New subscriber registered: {chat_id}")
        except Exception as e:
            logger.error(f"Failed to save subscriber {chat_id}: {e}")

def unregister_subscriber(chat_id: int) -> None:
    """
    Видаляє користувача зі списку підписників (наприклад, якщо бот заблоковано).
    """
    global _SUBSCRIBERS_CACHE
    if _SUBSCRIBERS_CACHE is None:
        get_subscribers()
    if chat_id in _SUBSCRIBERS_CACHE:
        _SUBSCRIBERS_CACHE.remove(chat_id)
        try:
            with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
                json.dump(list(_SUBSCRIBERS_CACHE), f, indent=2)
            logger.info(f"Subscriber removed (blocked or inactive): {chat_id}")
        except Exception as e:
            logger.error(f"Failed to remove subscriber {chat_id}: {e}")
