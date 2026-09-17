from datetime import date, timedelta
from typing import Optional



SCHEDULE_TRANSFERS: dict[date, dict] = {
    date(2026, 9, 19): {
        "target_day_name": "ПОНЕДІЛОК",
        "target_date": date(2026, 11, 30)
    },
    date(2026, 9, 26): {
        "target_day_name": "ВІВТОРОК",
        "target_date": date(2026, 12, 1)
    },
    date(2026, 10, 3): {
        "target_day_name": "СЕРЕДА",
        "target_date": date(2026, 12, 2)
    },
    date(2026, 10, 10): {
        "target_day_name": "ЧЕТВЕР",
        "target_date": date(2026, 12, 3),

    },
    date(2026, 10, 17): {
        "target_day_name": "П’ЯТНИЦЯ",
        "target_date": date(2026, 12, 4),


    },
    date(2026, 10, 24): {
        "target_day_name": "ПОНЕДІЛОК",
        "target_date": date(2026, 12, 7),

    },
    date(2026, 10, 31): {
        "target_day_name": "ВІВТОРОК",
        "target_date": date(2026, 12, 8),

    },
    date(2026, 11, 7): {
        "target_day_name": "СЕРЕДА",
        "target_date": date(2026, 12, 9),

    },
    date(2026, 11, 14): {
        "target_day_name": "ЧЕТВЕР",
        "target_date": date(2026, 12, 10),

    },
    date(2026, 11, 21): {
        "target_day_name": "П’ЯТНИЦЯ",
        "target_date": date(2026, 12, 11),
    }
}

# Оригінальні дати, з яких пари перенесені на суботи (у цей період проходить екзаменаційна сесія)
VACATED_DATES: dict[date, dict] = {
    info["target_date"]: {
        "transferred_to": saturday,
        "transferred_to_ua": saturday.strftime("%d.%m.%Y"),
        "original_day_name": info["target_day_name"],
        "reason": f"Аудиторні заняття перенесено на суботу {saturday.strftime('%d.%m.%Y')} згідно з наказом ректора (екзаменаційна сесія)."
    }
    for saturday, info in SCHEDULE_TRANSFERS.items()
}

def is_working_saturday(d: date) -> bool:
    """Перевіряє, чи є дата робочою суботою з перенесеними заняттями."""
    return d in SCHEDULE_TRANSFERS

def get_day_transfer(d: date) -> Optional[dict]:
    """Повертає інформацію про перенесення занять, якщо день є робочою суботою."""
    return SCHEDULE_TRANSFERS.get(d)

def is_vacated_date(d: date) -> bool:
    """Перевіряє, чи була пара з цього дня перенесена на суботу."""
    return d in VACATED_DATES

def get_vacated_info(d: date) -> Optional[dict]:
    """Повертає інформацію про звільнений день."""
    return VACATED_DATES.get(d)

def is_study_day(d: date) -> bool:
    """
    Визначає, чи є день навчальним.
    Пн-Пт — навчальні (крім днів, які перенесені або канікули).
    Субота — навчальна тільки якщо є робочою суботою.
    Неділя — завжди вихідний.
    """
    if d.weekday() < 5:
        # Пн-Пт навчальні, якщо не звільнені
        return not is_vacated_date(d)
    elif d.weekday() == 5:
        return is_working_saturday(d)
    return False

def get_next_study_day(current_date: date) -> date:
    """
    Знаходить наступний навчальний день з урахуванням робочих субот.
    """
    step_date = current_date + timedelta(days=1)
    for _ in range(7):
        if is_study_day(step_date):
            return step_date
        # Якщо звичайний робочий день без пар (наприклад vacated), але користувач гортає по днях
        if step_date.weekday() < 5:
            return step_date
        step_date += timedelta(days=1)
    return current_date + timedelta(days=1)

def get_prev_study_day(current_date: date) -> date:
    """
    Знаходить попередній навчальний день з урахуванням робочих субот.
    """
    step_date = current_date - timedelta(days=1)
    for _ in range(7):
        if is_study_day(step_date):
            return step_date
        if step_date.weekday() < 5:
            return step_date
        step_date -= timedelta(days=1)
    return current_date - timedelta(days=1)

def get_week_study_days(target_date: date) -> list[tuple[str, date]]:
    """
    Повертає список навчальних днів поточного тижня:
    - Якщо в суботу цього тижня є заняття: [Пн, Вт, Ср, Чт, Пт, Сб]
    - Інакше: [Пн, Вт, Ср, Чт, Пт]
    """
    weekday = target_date.weekday()
    monday = target_date - timedelta(days=weekday)
    saturday = monday + timedelta(days=5)

    base_labels = [("Пн", monday),
                   ("Вт", monday + timedelta(days=1)),
                   ("Ср", monday + timedelta(days=2)),
                   ("Чт", monday + timedelta(days=3)),
                   ("Пт", monday + timedelta(days=4))]

    if is_working_saturday(saturday) or target_date == saturday:
        base_labels.append(("Сб", saturday))

    return base_labels
