from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Returns main persistent reply keyboard with quick actions.
    """
    kb = [
        [
            KeyboardButton(text="📅 Сьогодні"),
            KeyboardButton(text="📅 Завтра")
        ],
        [
            KeyboardButton(text="🗓 Непарний тиждень (чисельник)"),
            KeyboardButton(text="🗓 Парний тиждень (знаменник)")
        ],
        [
            KeyboardButton(text="📆 Обрати день"),
            KeyboardButton(text="ℹ️ Поточний тиждень")
        ],
        [
            KeyboardButton(text="🔄 Оновити розклад")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_days_inline_keyboard(prefix: str = "day") -> InlineKeyboardMarkup:
    """
    Returns inline buttons for Monday to Friday.
    """
    days = [
        ("Пн", "ПОНЕДІЛОК"),
        ("Вт", "ВІВТОРОК"),
        ("Ср", "СЕРЕДА"),
        ("Чт", "ЧЕТВЕР"),
        ("Пт", "П’ЯТНИЦЯ")
    ]
    buttons = [
        InlineKeyboardButton(text=label, callback_data=f"{prefix}:{day}")
        for label, day in days
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

def get_week_choice_inline_keyboard(day_name: str) -> InlineKeyboardMarkup:
    """
    Inline keyboard to choose parity for a specific day.
    """
    buttons = [
        [
            InlineKeyboardButton(text="🟢 Непарний (чисельник)", callback_data=f"showday:{day_name}:odd"),
            InlineKeyboardButton(text="🔵 Парний (знаменник)", callback_data=f"showday:{day_name}:even")
        ],
        [
            InlineKeyboardButton(text="📋 Всі пари на день", callback_data=f"showday:{day_name}:all")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
