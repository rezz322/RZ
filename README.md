# GG WP — Telegram-бот розкладу групи РЗ-263 🎓

Автоматизований Telegram-бот для моніторингу та перегляду розкладу групи **РЗ-263** (ІІБРТ, Одеська політехніка) на базі `aiogram 3`.

---

## ✨ Основні можливості

* 📅 **Миттєвий розклад по днях**: Зручна навігація днями тижня за допомогою інлайн-кнопок (`⬅️ День назад`, `День вперед ➡️`, `Пн`–`Пт`, `📅 Сьогодні`).
* ⚡ **Блискавична швидкість**: Розклад зберігається в in-memory кеші (швидкість рендеру ~0.09 мс).
* 🔔 **Нагадування за 10 хвилин**: Автоматичне надсилання сповіщень усім підписникам за 10 хвилин до початку пари з прямими посиланнями на Zoom/Google Meet.
* 👥 **Підтримка підгруп та кількох викладачів**: Коректний розбір викладачів із закріпленням за кожним окремих посилань на пару.
* 🔄 **Автоматичне відстеження змін у розкладі**: Моніторинг Google Drive та оновлення даних при виході нових версій розкладу.
* 🐳 **Підтримка Docker & Docker Compose**: Готові файли для деплою на сервері з правильною таймзоною `Europe/Kyiv`.

---

## 🛠 Налаштування та запуск

### 1. Створення файлу `.env`
Скопіюйте `.env.example` у `.env`:
```bash
cp .env.example .env
```
Відкрийте `.env` і вставте токен вашого бота від `@BotFather`:
```ini
BOT_TOKEN=ваш_токен_від_BotFather
GROUP_NAME=РЗ-263
GDRIVE_FOLDER_ID=1Jlt45-PyFNJjfbNw1UVHWQ9GxzT5xizo
SEMESTER_START=2026-08-31
CHECK_INTERVAL_SECONDS=1800
ALERT_MINUTES_BEFORE=10

# База даних MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=rz263_bot
MYSQL_USER=rz_user
MYSQL_PASSWORD=rz_password
MYSQL_ROOT_PASSWORD=rz_root_password
```

---

## 🚀 Запуск бота

### Спосіб 1: Через Docker (рекомендовано для сервера)
Docker Compose автоматично запускає контейнер MySQL 8.0 та бота в спільній мережі з постійним збереженням даних:
```bash
# Запуск у фоновому режимі (MySQL + Bot)
docker compose up -d --build

# Перегляд логів
docker compose logs -f

# Зупинка
docker compose down
```

### Спосіб 2: Локальний запуск через Python
```bash
pip install -r requirements.txt
python main.py
```
*(При відсутності активного локального сервера MySQL бот автоматично переходить у режим file-fallback на `data/subscribers.json` без аварійного завершення).*

### Тестовий парсинг без запуску бота в Telegram:
```bash
python main.py --test
```

---

## 📁 Структура проєкту

```
.
├── bot/
│   ├── handlers.py         # Маршрутизація команд та інлайн-колбеків
│   ├── keyboards.py        # Інлайн-навігація днями тижня
│   ├── templates.py        # Усі текстові шаблони та розклад дзвінків
│   ├── utils.py            # Керування підписниками та in-memory кеш розкладу
│   └── scheduler.py        # Фоновий моніторинг та нагадування про пари
├── database/
│   ├── __init__.py
│   └── db.py               # Асинхронне підключення до MySQL (aiomysql)
├── parser/
│   ├── monitor.py          # Перевірка змін у Google Drive
│   └── schedule_parser.py  # Парсер DOCX розкладу у schedule.json
├── data/
│   ├── schedule.json       # Кеш розкладу для групи РЗ-263
│   └── subscribers.json    # Резервний список підписників
├── Dockerfile              # Docker-образ із таймзоною Europe/Kyiv
├── docker-compose.yml      # Compose: сервіси MySQL 8.0 та Bot
├── config.py               # Конфігурація проєкту
├── main.py                 # Точка входу, ініціалізація БД та фонових процесів
├── requirements.txt        # Список бібліотек (aiogram, aiomysql тощо)
├── .env.example            # Шаблон конфігурації
└── README.md
```
