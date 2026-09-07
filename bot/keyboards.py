from datetime import date, timedelta
from aiogram.types import (
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

def get_remove_keyboard() -> ReplyKeyboardRemove:
    """
    Видаляє будь-яку збережену нижню Reply-клавіатуру у клієнта.
    """
    return ReplyKeyboardRemove()

def get_day_navigation_keyboard(target_date: date) -> InlineKeyboardMarkup:
    """
    Генерує інлайн-навігацію розкладу:
    - Стрілки: день назад / день вперед (з автоматичним пропуском вихідних).
    - Кнопки робочих днів тижня (Пн - Пт) із позначкою активного дня.
    - Кнопка повернення до сьогоднішнього дня.
    """
    weekday = target_date.weekday()

    # Розрахунок переходів між робочими днями
    if weekday == 0:  # Понеділок -> назад у п'ятницю минулого тижня
        prev_date = target_date - timedelta(days=3)
        next_date = target_date + timedelta(days=1)
    elif weekday == 4:  # П'ятниця -> вперед у понеділок наступного тижня
        prev_date = target_date - timedelta(days=1)
        next_date = target_date + timedelta(days=3)
    elif weekday == 5:  # Субота
        prev_date = target_date - timedelta(days=1)
        next_date = target_date + timedelta(days=2)
    elif weekday == 6:  # Неділя
        prev_date = target_date - timedelta(days=2)
        next_date = target_date + timedelta(days=1)
    else:  # Вівторок, Середа, Четвер
        prev_date = target_date - timedelta(days=1)
        next_date = target_date + timedelta(days=1)

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

    # Рядок 2: Кнопки днів тижня (Пн - Пт)
    monday = target_date - timedelta(days=weekday if weekday < 5 else 0)
    day_labels = ["Пн", "Вт", "Ср", "Чт", "Пт"]
    row_days = []

    for i, label in enumerate(day_labels):
        day_date = monday + timedelta(days=i)
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
