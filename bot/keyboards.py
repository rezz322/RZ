from datetime import date
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from bot.transfers import (
    get_prev_study_day,
    get_next_study_day,
    get_week_study_days
)

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Повертає постійну нижню Reply-клавіатуру з кнопкою для швидкого перегляду розкладу.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Розклад")]
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Натисніть «📅 Розклад» або оберіть дію..."
    )

def get_remove_keyboard() -> ReplyKeyboardRemove:
    """
    Видаляє будь-яку збережену нижню Reply-клавіатуру у клієнта.
    """
    return ReplyKeyboardRemove()

def get_day_navigation_keyboard(target_date: date) -> InlineKeyboardMarkup:
    """
    Генерує інлайн-навігацію розкладу:
    - Стрілки: день назад / день вперед (з автоматичним урахуванням робочих субот).
    - Кнопки робочих днів тижня (Пн - Пт або Пн - Сб, якщо є робоча субота).
    - Кнопка повернення до сьогоднішнього дня.
    """
    prev_date = get_prev_study_day(target_date)
    next_date = get_next_study_day(target_date)

    # Рядок 1: Стрілки
    row_arrows = [
        InlineKeyboardButton(
            text="⬅️ День назад",
            callback_data=f"nav:{prev_date.isoformat()}"
        ),
        InlineKeyboardButton(
            text="День вперед ➡️",
            callback_data=f"nav:{next_date.isoformat()}"
        )
    ]

    # Рядок 2: Кнопки навчальних днів поточного тижня (динамічно Пн-Пт або Пн-Сб)
    study_days = get_week_study_days(target_date)
    row_days = []

    for label, day_date in study_days:
        is_active = (day_date == target_date)
        btn_text = f"• {label} •" if is_active else label
        row_days.append(
            InlineKeyboardButton(
                text=btn_text,
                callback_data="noop" if is_active else f"nav:{day_date.isoformat()}"
            )
        )

    keyboard = [row_arrows, row_days]

    # Рядок 3: Повернення до сьогодні
    today = date.today()
    if target_date != today:
        keyboard.append([
            InlineKeyboardButton(
                text="📅 Повернутись до Сьогодні",
                callback_data=f"nav:{today.isoformat()}"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
