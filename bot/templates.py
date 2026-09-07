import re
from datetime import date

PAIR_TIMES = {
    "1": "08:00 – 09:35",
    "2": "09:50 – 11:25",
    "3": "11:40 – 13:15",
    "4": "13:30 – 15:05",
    "5": "15:20 – 16:55"
}

URL_PATTERN = re.compile(r'https?://[^\s<>"]+')
ZOOM_ID_PATTERN = re.compile(r'(?:ідентифікатор|конференція|№:?|id:?)\s*[:.]?\s*(\d{3}[\s-]?\d{3,4}[\s-]?\d{3,4})', re.IGNORECASE)
ZOOM_PWD_PATTERN = re.compile(r'(?:код(?: доступа| конференції)?|пароль|pwd:?)\s*[:.]?\s*([A-Za-z0-9]+)', re.IGNORECASE)
SKIP_LINE_PATTERN = re.compile(r'(?:ідентифікатор|код конференції|код доступа|конференція zoom)', re.IGNORECASE)

TEACHER_MARKERS = re.compile(
    r'(?:ст\.?\s*викладач|доц(?:ент|\.)?|проф(?:есор|\.)?|св\.|асистент|[А-ЯІЇЄ][а-яіїє]+\s+[А-ЯІЇЄ]\.?\s*[А-ЯІЇЄ]\.?|[А-ЯІЇЄ][а-яіїє]+\s+[А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)?)',
    re.IGNORECASE
)

def get_link_label(url: str) -> str:
    """
    Повертає зрозумілу назву платформи за URL.
    """
    url_lower = url.lower()
    if "zoom.us" in url_lower:
        return "Zoom"
    elif "meet.google.com" in url_lower:
        return "Google Meet"
    elif "classroom.google.com" in url_lower:
        return "Classroom"
    return "Підключитись"

def extract_teachers_with_links(lesson: dict) -> list[dict]:
    """
    Аналізує сирий текст заняття та прив'язує посилання до конкретного викладача.
    """
    raw_text = lesson.get("raw_text", "")
    if not raw_text:
        return [{
            "teacher": lesson.get("teacher", ""),
            "urls": lesson.get("urls", []),
            "meeting_id": lesson.get("meeting_id"),
            "passcode": lesson.get("passcode")
        }]

    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    if not lines:
        return []

    content_lines = lines[1:]

    chunks = []
    current_teacher = None
    current_urls = []
    current_id = None
    current_pwd = None

    for line in content_lines:
        urls_in_line = URL_PATTERN.findall(line)
        line_clean = URL_PATTERN.sub("", line).strip()

        m_id = ZOOM_ID_PATTERN.search(line)
        m_pwd = ZOOM_PWD_PATTERN.search(line)
        if m_id:
            current_id = m_id.group(1).strip()
        if m_pwd:
            current_pwd = m_pwd.group(1).strip()

        if SKIP_LINE_PATTERN.search(line_clean):
            continue

        is_teacher = False
        if line_clean and not line_clean.isdigit():
            if TEACHER_MARKERS.search(line_clean) or line_clean.endswith(":"):
                is_teacher = True

        if is_teacher:
            if current_teacher:
                chunks.append({
                    "teacher": current_teacher.rstrip(":").strip(),
                    "urls": current_urls,
                    "meeting_id": current_id or lesson.get("meeting_id"),
                    "passcode": current_pwd or lesson.get("passcode")
                })
                current_urls = []
                current_id = None
                current_pwd = None

            current_teacher = line_clean.rstrip(":").strip()
            current_urls.extend(urls_in_line)
            if m_id:
                current_id = m_id.group(1).strip()
            if m_pwd:
                current_pwd = m_pwd.group(1).strip()
        else:
            current_urls.extend(urls_in_line)

    if current_teacher:
        chunks.append({
            "teacher": current_teacher.rstrip(":").strip(),
            "urls": current_urls,
            "meeting_id": current_id or lesson.get("meeting_id"),
            "passcode": current_pwd or lesson.get("passcode")
        })

    if not chunks:
        chunks.append({
            "teacher": lesson.get("teacher", ""),
            "urls": lesson.get("urls", []),
            "meeting_id": lesson.get("meeting_id"),
            "passcode": lesson.get("passcode")
        })

    return chunks

def format_lesson_entry_html(lesson: dict) -> str:
    """
    Форматує один запис заняття:
    - Якщо кілька викладачів — для кожного окремо вказує його ім'я та закріплені за ним посилання.
    - Якщо один викладач — виводить стандартний компактний блок.
    """
    l_type = f"<i>[{lesson['type'].strip()}]</i> " if lesson.get("type") else ""
    subject = lesson.get("subject", "Без назви")
    lines = [f"📖 {l_type}<b>{subject}</b>"]

    teachers = extract_teachers_with_links(lesson)

    if len(teachers) > 1:
        for t in teachers:
            lines.append(f"  👤 <b>{t['teacher']}</b>")
            if t["urls"]:
                links = [f"<a href='{u}'>{get_link_label(u)}</a>" for u in t["urls"]]
                lines.append("     🔗 " + " | ".join(links))
            if t.get("meeting_id"):
                pwd_str = f" | Код: <code>{t['passcode']}</code>" if t.get("passcode") else ""
                lines.append(f"     🔑 ID: <code>{t['meeting_id']}</code>{pwd_str}")
    elif len(teachers) == 1:
        t = teachers[0]
        if t.get("teacher"):
            lines.append(f"  👤 {t['teacher']}")
        if t.get("urls"):
            links = [f"<a href='{u}'>{get_link_label(u)}</a>" for u in t["urls"]]
            lines.append("  🔗 " + " | ".join(links))
        if t.get("meeting_id"):
            pwd_str = f" | Код: <code>{t['passcode']}</code>" if t.get("passcode") else ""
            lines.append(f"  🔑 ID: <code>{t['meeting_id']}</code>{pwd_str}")

    return "\n".join(lines)

def format_day_schedule_text(
    target_date: date,
    day_name: str,
    pairs_dict: dict,
    week_num: int,
    parity: str,
    parity_ua: str,
    filter_func=None
) -> str:
    """
    Форматує повний текст розкладу на день у HTML.
    """
    date_formatted = target_date.strftime("%d.%m.%Y")
    header = (
        f"📅 <b>{day_name}</b>, <code>{date_formatted}</code>\n"
        f"ℹ️ <b>{week_num}-й тиждень</b> ({parity_ua})\n"
    )

    if day_name in ["СУБОТА", "НЕДІЛЯ"]:
        return (
            f"{header}\n"
            f"🏖 <i>Вихідний день! Занять немає.</i>\n\n"
            f"👉 <i>Скористайтеся стрілками або кнопками нижче для перегляду робочих днів (Пн–Пт).</i>"
        )

    msg = [header]
    has_lessons = False

    for p_num in sorted(pairs_dict.keys(), key=lambda x: int(x) if x.isdigit() else 99):
        raw_lessons = pairs_dict[p_num]
        lessons = filter_func(raw_lessons, week_num, parity) if filter_func else raw_lessons

        if not lessons:
            continue

        has_lessons = True
        time_slot = PAIR_TIMES.get(p_num, "")
        time_hint = f" ({time_slot})" if time_slot else ""
        msg.append(f"⏰ <b>{p_num} пара</b>{time_hint}:")

        for l in lessons:
            msg.append(format_lesson_entry_html(l))
            msg.append("")

    if not has_lessons:
        msg.append("🎉 <i>На цей день занять немає або пари відсутні у розкладі!</i>")

    return "\n".join(msg).strip()

def format_lesson_alert_text(pair_num: str, time_info: dict, lessons: list[dict], minutes_left: int = 10) -> str:
    """
    Форматує повідомлення-нагадування про початок пари за 10 хвилин з персоналізованими посиланнями викладачів.
    """
    msg = [
        f"🔔 <b>УВАГА! Через {minutes_left} хв розпочнеться {pair_num} пара!</b>",
        f"⏰ Час: <b>{time_info['start']} – {time_info['end']}</b>\n"
    ]

    for l in lessons:
        msg.append(format_lesson_entry_html(l))
        msg.append("")

    msg.append("🚀 <i>Приєднуйтесь до пари!</i>")
    return "\n".join(msg).strip()

def format_schedule_update_alert_text(meta: dict, group_name: str) -> str:
    """
    Форматує сповіщення про оновлення розкладу на сайті.
    """
    return (
        f"🔔 <b>УВАГА! РОЗКЛАД ОНОВЛЕНО НА САЙТІ ФАКУЛЬТЕТУ!</b>\n\n"
        f"• Документ: <code>{meta.get('title', 'Новий розклад')}</code>\n"
        f"• Дата модифікації: <b>{meta.get('last_modified', 'щойно')}</b>\n"
        f"• Група: <b>{group_name}</b>\n\n"
        f"Бот уже завантажив нову версію розкладу!"
    )

def format_no_schedule_text() -> str:
    """
    Повідомлення, коли розклад ще не завантажено.
    """
    return "⚠️ Розклад ще завантажується або оновлюється."
