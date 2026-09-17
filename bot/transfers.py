from datetime import date, timedelta
from typing import Optional

# Наказ ректора про перенесення аудиторних занять на суботи
# (для здобувачів першого бакалаврського рівня вищої освіти):
# 1. пн 30.11 (парний)    -> сб 19.09
# 2. вт 01.12 (парний)    -> сб 26.09
# 3. ср 02.12 (парний)    -> сб 03.10
# 4. чт 03.12 (парний)    -> сб 10.10
# 5. пт 04.12 (парний)    -> сб 17.10
# 6. пн 07.12 (непарний)  -> сб 24.10
# 7. вт 08.12 (непарний)  -> сб 31.10
# 8. ср 09.12 (непарний)  -> сб 07.11
# 9. чт 10.12 (непарний)  -> сб 14.11
# 10. пт 11.12 (непарний) -> сб 21.11

SCHEDULE_TRANSFERS: dict[date, dict] = {
    date(2026, 9, 19): {
        "target_day_name": "ПОНЕДІЛОК",
        "target_date": date(2026, 11, 30),
        "parity": "even",
        "parity_ua": "Парний тиждень (знаменник)",
        "week_number": 14,
        "note": "Відпрацювання за понеділок 30.11 (парний тиждень)",
        "order_hint": "Згідно з наказом ректора про перенесення аудиторних занять"
    },
    date(2026, 9, 26): {
        "target_day_name": "ВІВТОРОК",
        "target_date": date(2026, 12, 1),
        "parity": "even",
        "parity_ua": "Парний тиждень (знаменник)",
        "week_number": 14,
        "note": "Відпрацювання за вівторок 01.12 (парний тиждень)",
        "order_hint": "Згідно з наказом ректора про перенесення аудиторних занять"
    },
    date(2026, 10, 3): {
        "target_day_name": "СЕРЕДА",
        "target_date": date(2026, 12, 2),
        "parity": "even",
        "parity_ua": "Парний тиждень (знаменник)",
        "week_number": 14,
        "note": "Відпрацювання за середу 02.12 (парний тиждень)",
        "order_hint": "Згідно з наказом ректора про перенесення аудиторних занять"
    },
    date(2026, 10, 10): {
        "target_day_name": "ЧЕТВЕР",
        "target_date": date(2026, 12, 3),
        "parity": "even",
        "parity_ua": "Парний тиждень (знаменник)",
        "week_number": 14,
        "note": "Відпрацювання за четвер 03.12 (парний тиждень)",
        "order_hint": "Згідно з наказом ректора про перенесення аудиторних занять"
    },
    date(2026, 10, 17): {
        "target_day_name": "П’ЯТНИЦЯ",
        "target_date": date(2026, 12, 4),
        "parity": "even",
        "parity_ua": "Парний тиждень (знаменник)",
        "week_number": 14,
        "note": "Відпрацювання за п’ятницю 04.12 (парний тиждень)",
        "order_hint": "Згідно з наказом ректора про перенесення аудиторних занять"
    },
    date(2026, 10, 24): {
        "target_day_name": "ПОНЕДІЛОК",
        "target_date": date(2026, 12, 7),
        "parity": "odd",
        "parity_ua": "Непарний тиждень (чисельник)",
        "week_number": 15,
        "note": "Відпрацювання за понеділок 07.12 (непарний тиждень)",
        "order_hint": "Згідно з наказом ректора про перенесення аудиторних занять"
    },
    date(2026, 10, 31): {
        "target_day_name": "ВІВТОРОК",
        "target_date": date(2026, 12, 8),
        "parity": "odd",
        "parity_ua": "Непарний тиждень (чисельник)",
        "week_number": 15,
        "note": "Відпрацювання за вівторок 08.12 (непарний тиждень)",
        "order_hint": "Згідно з наказом ректора про перенесення аудиторних занять"
    },
    date(2026, 11, 7): {
        "target_day_name": "СЕРЕДА",
        "target_date": date(2026, 12, 9),
        "parity": "odd",
        "parity_ua": "Непарний тиждень (чисельник)",
        "week_number": 15,
        "note": "Відпрацювання за середу 09.12 (непарний тиждень)",
        "order_hint": "Згідно з наказом ректора про перенесення аудиторних занять"
    },
    date(2026, 11, 14): {
        "target_day_name": "ЧЕТВЕР",
        "target_date": date(2026, 12, 10),
        "parity": "odd",
        "parity_ua": "Непарний тиждень (чисельник)",
        "week_number": 15,
        "note": "Відпрацювання за четвер 10.12 (непарний тиждень)",
        "order_hint": "Згідно з наказом ректора про перенесення аудиторних занять"
    },
    date(2026, 11, 21): {
        "target_day_name": "П’ЯТНИЦЯ",
        "target_date": date(2026, 12, 11),
        "parity": "odd",
        "parity_ua": "Непарний тиждень (чисельник)",
        "week_number": 15,
        "note": "Відпрацювання за п’ятницю 11.12 (непарний тиждень)",
        "order_hint": "Згідно з наказом ректора про перенесення аудиторних занять"
    }
}

# Оригінальні дати, з яких пари перенесені на суботи (у цей період проходить екзаменаційна сесія)
VACATED_DATES: dict[date, dict] = {
    info["target_date"]: {
        "transferred_to": saturday,
        "transferred_to_ua": saturday.strftime("%d.%m.%Y"),
        "original_day_name": info["target_day_name"],
        "parity": info["parity"],
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
