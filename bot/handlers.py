import asyncio
import logging
from datetime import date
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, LinkPreviewOptions
from aiogram.exceptions import TelegramBadRequest

from config import GROUP_NAME
from parser.schedule_parser import (
    get_academic_week_info,
    filter_lessons_for_week,
    download_and_parse_schedule
)
from parser.monitor import (
    fetch_latest_schedule_meta,
    has_schedule_changed,
    save_schedule_meta
)
from bot.keyboards import get_day_navigation_keyboard, get_remove_keyboard
from bot.templates import (
    format_day_schedule_text,
    format_lesson_alert_text,
    format_no_schedule_text
)
from bot.utils import (
    get_cached_schedule,
    reload_cached_schedule,
    register_subscriber
)
from bot.scheduler import LESSON_TIMES

logger = logging.getLogger(__name__)
router = Router()

async def render_schedule_message(target_date: date) -> tuple[str, any]:
    """
    Підготовлює текст розкладу та навігаційну інлайн-клавіатуру з пам'яті (0ms).
    """
    schedule = get_cached_schedule()
    if not schedule:
        return format_no_schedule_text(), None

    week_info = get_academic_week_info(target_date)
    day_name = week_info["day_name"]
    pairs = schedule.get("days", {}).get(day_name, {})

    text = format_day_schedule_text(
        target_date=target_date,
        day_name=day_name,
        pairs_dict=pairs,
        week_num=week_info["week_number"],
        parity=week_info["parity"],
        parity_ua=week_info["parity_ua"],
        filter_func=filter_lessons_for_week
    )
    markup = get_day_navigation_keyboard(target_date)
    return text, markup

@router.message(CommandStart())
@router.message(Command("today"))
@router.message(Command("schedule"))
@router.message(F.text.in_(["Розклад", "розклад"]))
async def cmd_start_and_schedule(message: Message):
    """
    Миттєво показує розклад на сьогодні за 1 запит без зайвих мережевих затримок.
    """
    user = message.from_user
    register_subscriber(
        message.chat.id,
        username=user.username if user else None,
        full_name=user.full_name if user else None
    )
    today = date.today()
    text, markup = await render_schedule_message(today)
    await message.answer(
        text,
        reply_markup=markup,
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )

@router.message(F.text == "📅 Розклад по днях")
async def cmd_old_button_cleanup(message: Message):
    """
    Обробник для старої клавіатури: показує розклад та прибирає збережену клавіатуру.
    """
    user = message.from_user
    register_subscriber(
        message.chat.id,
        username=user.username if user else None,
        full_name=user.full_name if user else None
    )
    try:
        rm = await message.answer("🗓 Оновлення...", reply_markup=get_remove_keyboard())
        await rm.delete()
    except Exception:
        pass

    today = date.today()
    text, markup = await render_schedule_message(today)
    await message.answer(
        text,
        reply_markup=markup,
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )

# Кеш активної дати по чатах для запобігання дублюючим запитам до Telegram
_LAST_CHAT_DATE: dict[int, str] = {}

@router.callback_query(F.data == "noop")
async def on_noop(callback: CallbackQuery):
    """
    Миттєва відповідь на клік по вже обраному дню (0ms без оновлення повідомлення).
    """
    await callback.answer()

@router.callback_query(F.data.startswith("nav:"))
async def on_navigate_day(callback: CallbackQuery):
    """
    Миттєве інлайн-перемикання між днями (паралельна обробка без затримок).
    """
    date_str = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id

    # Якщо цей день вже відображається — просто підтверджуємо клік
    if _LAST_CHAT_DATE.get(chat_id) == date_str:
        await callback.answer()
        return

    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        await callback.answer("Некоректна дата!", show_alert=True)
        return

    _LAST_CHAT_DATE[chat_id] = date_str
    text, markup = await render_schedule_message(target_date)

    # Миттєво гасимо спінер на кнопці у фоні без блокування
    async def _safe_answer():
        try:
            await callback.answer()
        except Exception:
            pass

    asyncio.create_task(_safe_answer())

    # Редагуємо повідомлення на обраний день
    try:
        await callback.message.edit_text(
            text,
            reply_markup=markup,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            logger.warning(f"Error updating day schedule: {e}")
    except Exception as e:
        logger.warning(f"Callback edit error: {e}")

@router.message(Command("check"))
async def cmd_check_updates(message: Message):
    """
    Ручна перевірка наявності свіжої версії розкладу на Google Drive.
    """
    register_subscriber(message.chat.id)
    status_msg = await message.answer("🔄 Перевіряю Google Drive факультету...")
    try:
        meta = await fetch_latest_schedule_meta()
        if not meta:
            await status_msg.edit_text("❌ Не вдалося отримати доступ до папки розкладу на Google Drive.")
            return

        is_changed = has_schedule_changed(meta)
        schedule = get_cached_schedule()

        if is_changed or not schedule:
            await status_msg.edit_text(
                f"📥 Знайдено новий файл: <b>{meta['title']}</b>. Завантажую та парсю...",
                parse_mode="HTML"
            )
            await download_and_parse_schedule(meta["file_id"])
            save_schedule_meta(meta)
            reload_cached_schedule()
            await status_msg.edit_text(
                f"✅ <b>Розклад успішно оновлено!</b>\n"
                f"• Документ: <code>{meta['title']}</code>\n"
                f"• Оновлено: {meta['last_modified']}\n"
                f"• Група: <b>{GROUP_NAME}</b>\n\n"
                f"Натисніть /start або скористайтесь стрілками для перегляду.",
                parse_mode="HTML"
            )
        else:
            await status_msg.edit_text(
                f"✅ У вас найактуальніша версія розкладу!\n"
                f"• Документ: <code>{meta['title']}</code>\n"
                f"• Остання зміна на Google Drive: {meta['last_modified']}",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.exception("Error checking updates")
        await status_msg.edit_text(f"❌ Помилка під час оновлення: {e}")

@router.message(Command("test_alert"))
async def cmd_test_alert(message: Message):
    """
    Тестове надсилання нагадування для перевірки форматування повідомлення про пару.
    """
    register_subscriber(message.chat.id)
    sample_lessons = [
        {
            "subject": "Вища математика",
            "type": "лекція",
            "teacher": "Св. Сікіраш Ю.Є.",
            "urls": ["https://us04web.zoom.us/j/8944225620?pwd=test"],
            "meeting_id": "8944225620",
            "passcode": "7SGuR7"
        }
    ]
    sample_time = LESSON_TIMES[1]  # 2 пара
    alert_text = format_lesson_alert_text("2", sample_time, sample_lessons, 10)
    await message.answer(
        f"<i>[ТЕСТОВЕ СПОВІЩЕННЯ]</i>\n\n{alert_text}",
        parse_mode="HTML",
        disable_web_page_preview=True
    )
