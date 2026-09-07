import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Load .env file with fallback if python-dotenv is not installed
env_path = BASE_DIR / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = val

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROUP_NAME = os.getenv("GROUP_NAME", "РЗ-263")
FACULTY_URL = os.getenv("FACULTY_URL", "https://op.edu.ua/studies/iibrt")
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "1Jlt45-PyFNJjfbNw1UVHWQ9GxzT5xizo")
SEMESTER_START = os.getenv("SEMESTER_START", "2026-08-31")  # Понеділок 1-го тижня
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "1800"))
ALERT_MINUTES_BEFORE = int(os.getenv("ALERT_MINUTES_BEFORE", "10"))

# MySQL Database settings
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "rz263_bot")
MYSQL_USER = os.getenv("MYSQL_USER", "rz_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "rz_password")
MYSQL_ROOT_PASSWORD = os.getenv("MYSQL_ROOT_PASSWORD", "rz_root_password")

SCHEDULE_FILE = DATA_DIR / "schedule.json"
META_FILE = DATA_DIR / "meta.json"
SUBSCRIBERS_FILE = DATA_DIR / "subscribers.json"
