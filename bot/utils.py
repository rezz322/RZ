import asyncio
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

def set_subscribers_cache(subscribers: list[int]) -> None:
    """
    Встановлює кеш підписників безпосередньо з бази даних.
    """
    global _SUBSCRIBERS_CACHE
    _SUBSCRIBERS_CACHE = set(subscribers)
    logger.info(f"Loaded {len(_SUBSCRIBERS_CACHE)} active subscribers into in-memory cache.")

def get_subscribers() -> list[int]:
    """
    Повертає список зареєстрованих підписників бота (з кешу або диску/БД).
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

async def async_register_subscriber(
    chat_id: int,
    username: str | None = None,
    full_name: str | None = None
) -> None:
    """
    Асинхронно зберігає підписника в MySQL та оновлює локальний кеш і бекап-файл.
    """
    global _SUBSCRIBERS_CACHE
    if _SUBSCRIBERS_CACHE is None:
        get_subscribers()
    _SUBSCRIBERS_CACHE.add(chat_id)

    from database.db import is_db_connected, register_subscriber_db
    if is_db_connected():
        await register_subscriber_db(chat_id, username, full_name)

    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(_SUBSCRIBERS_CACHE), f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save subscriber backup {chat_id}: {e}")

def register_subscriber(
    chat_id: int,
    username: str | None = None,
    full_name: str | None = None
) -> None:
    """
    Синхронна обгортка: миттєво додає в RAM та запускає фонове збереження в MySQL.
    """
    global _SUBSCRIBERS_CACHE
    if _SUBSCRIBERS_CACHE is None:
        get_subscribers()

    need_persist = chat_id not in _SUBSCRIBERS_CACHE
    _SUBSCRIBERS_CACHE.add(chat_id)

    if need_persist:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(async_register_subscriber(chat_id, username, full_name))
        except RuntimeError:
            asyncio.run(async_register_subscriber(chat_id, username, full_name))

async def async_unregister_subscriber(chat_id: int) -> None:
    """
    Асинхронно позначає підписника неактивним в MySQL та видаляє з оперативного кешу.
    """
    global _SUBSCRIBERS_CACHE
    if _SUBSCRIBERS_CACHE is None:
        get_subscribers()
    _SUBSCRIBERS_CACHE.discard(chat_id)

    from database.db import is_db_connected, unregister_subscriber_db
    if is_db_connected():
        await unregister_subscriber_db(chat_id)

    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(_SUBSCRIBERS_CACHE), f, indent=2)
        logger.info(f"Subscriber removed: {chat_id}")
    except Exception as e:
        logger.error(f"Failed to remove subscriber {chat_id}: {e}")

def unregister_subscriber(chat_id: int) -> None:
    """
    Синхронна обгортка для видалення користувача.
    """
    global _SUBSCRIBERS_CACHE
    if _SUBSCRIBERS_CACHE is not None:
        _SUBSCRIBERS_CACHE.discard(chat_id)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(async_unregister_subscriber(chat_id))
    except RuntimeError:
        asyncio.run(async_unregister_subscriber(chat_id))
