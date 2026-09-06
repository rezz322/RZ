import json
import logging
from datetime import date, timedelta
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from config import SUBSCRIBERS_FILE, GROUP_NAME
from parser.schedule_parser import (
    load_schedule,
    get_academic_week_info,
    filter_lessons_for_week,
    download_and_parse_schedule,
    DAYS_ORDER
)
from parser.monitor import fetch_latest_schedule_meta, has_schedule_changed, save_schedule_meta
from bot.keyboards import (
    get_main_keyboard,
    get_days_inline_keyboard,
    get_week_choice_inline_keyboard
)

logger = logging.getLogger(__name__)
router = Router()

PAIR_TIMES = {
    "1": "08:00 – 09:35",
    "2": "09:50 – 11:25",
    "3": "11:40 – 13:15",
    "4": "13:30 – 15:05",
    "5": "15:20 – 16:55"
}

def register_subscriber(chat_id: int):
    """
    Saves user chat_id to subscribers list for update broadcasts.
    """
    subscribers = set()
    if SUBSCRIBERS_FILE.exists():
        try:
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                subscribers = set(json.load(f))
        except Exception:
            subscribers = set()
            
    subscribers.add(chat_id)
    with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(subscribers), f, indent=2)

def format_day_schedule(day_name: str, pairs_dict: dict, week_num: int = None, parity: str = None) -> str:
    """
    Formats day schedule into readable HTML message.
    """
    title_parity = ""
    if parity == "odd":
        title_parity = " (Непарний тиждень / чисельник)"
    elif parity == "even":
        title_parity = " (Парний тиждень / знаменник)"
        
    week_str = f" | {week_num} тиждень" if week_num else ""
    msg = [f"📅 <b>{day_name}</b>{title_parity}{week_str}\n"]
    
    has_lessons = False
    
    # Sort pairs 1..5
    for p_num in sorted(pairs_dict.keys(), key=lambda x: int(x) if x.isdigit() else 99):
        lessons = pairs_dict[p_num]
        
        # If filtering by week/parity is requested
        if parity:
            lessons = filter_lessons_for_week(lessons, week_num or 1, parity)
            
        if not lessons:
            continue
            
        has_lessons = True
        time_slot = PAIR_TIMES.get(p_num, "")
        time_hint = f" ({time_slot})" if time_slot else ""
        msg.append(f"⏰ <b>{p_num} пара</b>{time_hint}:")
        
        for l in lessons:
            l_type = f"<i>[{l['type']}]</i> " if l.get("type") else ""
            subject = l.get("subject", "Без назви")
            teacher = f"\n  👤 {l['teacher']}" if l.get("teacher") else ""
            
            # Format URLs
            urls = l.get("urls", [])
            links_text = ""
            if urls:
                links_text = "\n  🔗 " + " | ".join([f"<a href='{u}'>Підключитись</a>" for u in urls])
                
            id_pwd = ""
            if l.get("meeting_id"):
                id_pwd += f"\n  🔑 ID: <code>{l['meeting_id']}</code>"
            if l.get("passcode"):
                id_pwd += f" | Код: <code>{l['passcode']}</code>"
                
            msg.append(f"  📖 {l_type}<b>{subject}</b>{teacher}{links_text}{id_pwd}")
        msg.append("")  # separator line
        
    if not has_lessons:
        msg.append("🎉 <i>Занять немає або вихідний день!</i>")
        
    return "\n".join(msg)

@router.message(CommandStart())
async def cmd_start(message: Message):
    register_subscriber(message.chat.id)
    week_info = get_academic_week_info()
    
    welcome_text = (
        f"👋 <b>Привіт!</b> Я бот розкладу для групи <b>{GROUP_NAME}</b> (ІІБРТ, Одеська політехніка).\n\n"
        f"📌 <b>Поточний стан:</b>\n"
        f"• Сьогодні: <b>{week_info['target_date']}</b> ({week_info['day_name']})\n"
        f"• Тиждень: <b>{week_info['week_number']}-й</b> ({week_info['parity_ua']})\n\n"
        f"Я автоматично моніторю зміни на сайті та надсилатиму сповіщення, якщо розклад оновиться.\n"
        f"Використовуйте кнопки нижче або команди для швидкого перегляду:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

@router.message(F.text == "ℹ️ Поточний тиждень")
@router.message(Command("week_info"))
async def cmd_week_info(message: Message):
    week_info = get_academic_week_info()
    text = (
        f"ℹ️ <b>Інформація про навчальний тиждень:</b>\n\n"
        f"• Дата: <b>{week_info['target_date']}</b> ({week_info['day_name']})\n"
        f"• Номер тижня: <b>{week_info['week_number']}</b>\n"
        f"• Тип тижня: <b>{week_info['parity_ua']}</b>\n\n"
        f"<i>💡 Непарний тиждень = чисельник (1, 3, 5...)\n"
        f"💡 Парний тиждень = знаменник (2, 4, 6...)</i>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📅 Сьогодні")
@router.message(Command("today"))
async def cmd_today(message: Message):
    schedule = load_schedule()
    if not schedule:
        await message.answer("⚠️ Розклад ще не завантажено. Натисніть '🔄 Оновити розклад'.")
        return
        
    today = date.today()
    week_info = get_academic_week_info(today)
    day_name = week_info["day_name"]
    
    if day_name in ["СУБОТА", "НЕДІЛЯ"]:
        await message.answer(
            f"🏖 Сьогодні <b>{day_name}</b>, вихідний!\n"
            f"Тиждень: {week_info['week_number']}-й ({week_info['parity_ua']}).\n"
            f"Перегляньте розклад на понеділок кнопкою '📅 Завтра' або '📆 Обрати день'.",
            parse_mode="HTML"
        )
        return
        
    pairs = schedule["days"].get(day_name, {})
    resp = format_day_schedule(
        day_name=day_name,
        pairs_dict=pairs,
        week_num=week_info["week_number"],
        parity=week_info["parity"]
    )
    await message.answer(resp, parse_mode="HTML", disable_web_page_preview=True)

@router.message(F.text == "📅 Завтра")
@router.message(Command("tomorrow"))
async def cmd_tomorrow(message: Message):
    schedule = load_schedule()
    if not schedule:
        await message.answer("⚠️ Розклад ще не завантажено. Натисніть '🔄 Оновити розклад'.")
        return
        
    tomorrow = date.today() + timedelta(days=1)
    week_info = get_academic_week_info(tomorrow)
    day_name = week_info["day_name"]
    
    if day_name in ["СУБОТА", "НЕДІЛЯ"]:
        # Suggest Monday
        days_ahead = (7 - tomorrow.weekday()) % 7
        monday_date = tomorrow + timedelta(days=days_ahead)
        monday_info = get_academic_week_info(monday_date)
        pairs = schedule["days"].get("ПОНЕДІЛОК", {})
        resp = (
            f"🏖 Завтра <b>{day_name}</b>, вихідний!\n"
            f"Ось розклад на найближчий <b>Понеділок</b> ({monday_info['target_date']}):\n\n"
            + format_day_schedule("ПОНЕДІЛОК", pairs, monday_info["week_number"], monday_info["parity"])
        )
        await message.answer(resp, parse_mode="HTML", disable_web_page_preview=True)
        return
        
    pairs = schedule["days"].get(day_name, {})
    resp = format_day_schedule(
        day_name=day_name,
        pairs_dict=pairs,
        week_num=week_info["week_number"],
        parity=week_info["parity"]
    )
    await message.answer(resp, parse_mode="HTML", disable_web_page_preview=True)

@router.message(F.text == "🗓 Непарний тиждень (чисельник)")
async def cmd_odd_week(message: Message):
    schedule = load_schedule()
    if not schedule:
        await message.answer("⚠️ Розклад ще не завантажено. Натисніть '🔄 Оновити розклад'.")
        return
        
    await message.answer("🟢 <b>РОЗКЛАД НА НЕПАРНИЙ ТИЖДЕНЬ (ЧИСЕЛЬНИК):</b>", parse_mode="HTML")
    for day in DAYS_ORDER:
        pairs = schedule["days"].get(day, {})
        text = format_day_schedule(day, pairs, week_num=1, parity="odd")
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)

@router.message(F.text == "🗓 Парний тиждень (знаменник)")
async def cmd_even_week(message: Message):
    schedule = load_schedule()
    if not schedule:
        await message.answer("⚠️ Розклад ще не завантажено. Натисніть '🔄 Оновити розклад'.")
        return
        
    await message.answer("🔵 <b>РОЗКЛАД НА ПАРНИЙ ТИЖДЕНЬ (ЗНАМЕННИК):</b>", parse_mode="HTML")
    for day in DAYS_ORDER:
        pairs = schedule["days"].get(day, {})
        text = format_day_schedule(day, pairs, week_num=2, parity="even")
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)

@router.message(F.text == "📆 Обрати день")
async def cmd_choose_day(message: Message):
    await message.answer(
        "Оберіть день тижня для перегляду розкладу:",
        reply_markup=get_days_inline_keyboard()
    )

@router.callback_query(F.data.startswith("day:"))
async def on_day_chosen(callback: CallbackQuery):
    day_name = callback.data.split(":")[1]
    await callback.message.edit_text(
        f"Оберіть варіант тижня для <b>{day_name}</b>:",
        reply_markup=get_week_choice_inline_keyboard(day_name),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("showday:"))
async def on_show_day(callback: CallbackQuery):
    _, day_name, choice = callback.data.split(":")
    schedule = load_schedule()
    if not schedule:
        await callback.answer("Розклад не знайдено!", show_alert=True)
        return
        
    pairs = schedule["days"].get(day_name, {})
    week_info = get_academic_week_info()
    
    if choice == "odd":
        text = format_day_schedule(day_name, pairs, week_num=1, parity="odd")
    elif choice == "even":
        text = format_day_schedule(day_name, pairs, week_num=2, parity="even")
    else:
        text = format_day_schedule(day_name, pairs)
        
    await callback.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()

@router.message(F.text == "🔄 Оновити розклад")
@router.message(Command("check"))
async def cmd_check_updates(message: Message):
    status_msg = await message.answer("🔄 Перевіряю Google Drive факультету...")
    try:
        meta = await fetch_latest_schedule_meta()
        if not meta:
            await status_msg.edit_text("❌ Не вдалося отримати доступ до папки розкладу на Google Drive.")
            return
            
        is_changed = has_schedule_changed(meta)
        schedule = load_schedule()
        
        if is_changed or not schedule:
            await status_msg.edit_text(f"📥 Знайдено новий файл: <b>{meta['title']}</b>. Завантажую та парсю...", parse_mode="HTML")
            await download_and_parse_schedule(meta["file_id"])
            save_schedule_meta(meta)
            await status_msg.edit_text(
                f"✅ <b>Розклад успішно оновлено!</b>\n"
                f"• Документ: <code>{meta['title']}</code>\n"
                f"• Оновлено: {meta['last_modified']}\n"
                f"• Група: <b>{GROUP_NAME}</b>",
                parse_mode="HTML"
            )
        else:
            await status_msg.edit_text(
                f"✅ У вас актуальна версія розкладу!\n"
                f"• Документ: <code>{meta['title']}</code>\n"
                f"• Остання зміна на Google Drive: {meta['last_modified']}",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.exception("Error checking updates")
        await status_msg.edit_text(f"❌ Помилка під час оновлення: {e}")
