import json
import logging
import aiomysql
from typing import Optional

from config import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_DATABASE,
    MYSQL_USER,
    MYSQL_PASSWORD,
    SUBSCRIBERS_FILE,
    SCHEDULE_FILE
)

logger = logging.getLogger(__name__)

_POOL: Optional[aiomysql.Pool] = None

CREATE_SUBSCRIBERS_TABLE = """
CREATE TABLE IF NOT EXISTS subscribers (
    chat_id BIGINT PRIMARY KEY,
    username VARCHAR(255) NULL,
    full_name VARCHAR(255) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

CREATE_SCHEDULE_CACHE_TABLE = """
CREATE TABLE IF NOT EXISTS schedule_cache (
    id INT PRIMARY KEY AUTO_INCREMENT,
    group_name VARCHAR(64) NOT NULL UNIQUE,
    file_id VARCHAR(128) NOT NULL,
    updated_at VARCHAR(64) NOT NULL,
    schedule_json LONGTEXT NOT NULL,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

async def init_db() -> bool:
    """
    Ініціалізує асинхронний пул підключень до MySQL, створює таблиці
    та виконує автоматичну міграцію наявних даних із файлів.
    Повертає True, якщо з'єднання з MySQL успішне, інакше False (fallback на файли).
    """
    global _POOL
    logger.info(f"Connecting to MySQL database at {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}...")
    try:
        _POOL = await aiomysql.create_pool(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            db=MYSQL_DATABASE,
            charset="utf8mb4",
            autocommit=True,
            minsize=2,
            maxsize=10,
            connect_timeout=10
        )
    except Exception as e:
        logger.warning(
            f"Failed to connect to MySQL ({e}). Bot will operate in file-fallback mode."
        )
        _POOL = None
        return False

    try:
        async with _POOL.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(CREATE_SUBSCRIBERS_TABLE)
                await cursor.execute(CREATE_SCHEDULE_CACHE_TABLE)
        logger.info("MySQL tables verified/created successfully.")

        # Автоматична міграція наявних підписників із файлу
        await _migrate_file_subscribers_to_db()

        # Автоматична міграція розкладу із файлу
        await _migrate_file_schedule_to_db()

        return True
    except Exception as e:
        logger.error(f"Error during MySQL initialization: {e}", exc_info=True)
        return False

async def close_db() -> None:
    """
    Коректно закриває пул з'єднань з MySQL.
    """
    global _POOL
    if _POOL is not None:
        _POOL.close()
        await _POOL.wait_closed()
        _POOL = None
        logger.info("MySQL connection pool closed.")

def is_db_connected() -> bool:
    return _POOL is not None

async def _migrate_file_subscribers_to_db() -> None:
    """
    Переносить збережені chat_id із data/subscribers.json у таблицю subscribers.
    """
    if not SUBSCRIBERS_FILE.exists() or _POOL is None:
        return

    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            ids = json.load(f)
        if not ids:
            return

        async with _POOL.acquire() as conn:
            async with conn.cursor() as cursor:
                for cid in ids:
                    await cursor.execute(
                        """
                        INSERT INTO subscribers (chat_id, is_active)
                        VALUES (%s, TRUE)
                        ON DUPLICATE KEY UPDATE is_active = TRUE
                        """,
                        (cid,)
                    )
        logger.info(f"Successfully migrated {len(ids)} subscribers from {SUBSCRIBERS_FILE} to MySQL.")
    except Exception as e:
        logger.warning(f"Error migrating subscribers from file to MySQL: {e}")

async def _migrate_file_schedule_to_db() -> None:
    """
    Переносить збережений schedule.json у таблицю schedule_cache.
    """
    if not SCHEDULE_FILE.exists() or _POOL is None:
        return

    try:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data or "group" not in data:
            return

        group_name = data.get("group", "")
        file_id = data.get("file_id", "")
        updated_at = data.get("updated_at", "")

        await save_schedule_db(group_name, file_id, updated_at, data)
        logger.info(f"Successfully migrated schedule for '{group_name}' to MySQL schedule_cache.")
    except Exception as e:
        logger.warning(f"Error migrating schedule from file to MySQL: {e}")

async def register_subscriber_db(
    chat_id: int,
    username: Optional[str] = None,
    full_name: Optional[str] = None
) -> bool:
    """
    Додає або поновлює підписника в базі даних MySQL.
    """
    if _POOL is None:
        return False
    try:
        async with _POOL.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO subscribers (chat_id, username, full_name, is_active)
                    VALUES (%s, %s, %s, TRUE)
                    ON DUPLICATE KEY UPDATE
                        username = VALUES(username),
                        full_name = VALUES(full_name),
                        is_active = TRUE
                    """,
                    (chat_id, username, full_name)
                )
        return True
    except Exception as e:
        logger.error(f"Failed to register subscriber {chat_id} in MySQL: {e}")
        return False

async def unregister_subscriber_db(chat_id: int) -> bool:
    """
    Позначає підписника як неактивного (is_active = FALSE).
    """
    if _POOL is None:
        return False
    try:
        async with _POOL.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE subscribers SET is_active = FALSE WHERE chat_id = %s",
                    (chat_id,)
                )
        return True
    except Exception as e:
        logger.error(f"Failed to unregister subscriber {chat_id} in MySQL: {e}")
        return False

async def get_active_subscribers_db() -> list[int]:
    """
    Повертає список активних chat_id з бази даних MySQL.
    """
    if _POOL is None:
        return []
    try:
        async with _POOL.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT chat_id FROM subscribers WHERE is_active = TRUE")
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"Failed to load subscribers from MySQL: {e}")
        return []

async def save_schedule_db(
    group_name: str,
    file_id: str,
    updated_at: str,
    schedule_data: dict
) -> bool:
    """
    Зберігає кеш розкладу в MySQL.
    """
    if _POOL is None:
        return False
    try:
        json_str = json.dumps(schedule_data, ensure_ascii=False)
        async with _POOL.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO schedule_cache (group_name, file_id, updated_at, schedule_json)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        file_id = VALUES(file_id),
                        updated_at = VALUES(updated_at),
                        schedule_json = VALUES(schedule_json)
                    """,
                    (group_name, file_id, updated_at, json_str)
                )
        return True
    except Exception as e:
        logger.error(f"Failed to save schedule to MySQL: {e}")
        return False

async def load_schedule_db(group_name: str) -> Optional[dict]:
    """
    Завантажує розклад з MySQL.
    """
    if _POOL is None:
        return None
    try:
        async with _POOL.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT schedule_json FROM schedule_cache WHERE group_name = %s",
                    (group_name,)
                )
                row = await cursor.fetchone()
                if row and row[0]:
                    return json.loads(row[0])
        return None
    except Exception as e:
        logger.error(f"Failed to load schedule from MySQL for '{group_name}': {e}")
        return None
