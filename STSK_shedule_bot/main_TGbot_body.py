from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import json
from datetime import datetime, timedelta

TOKEN = '7740720807:AAE8WCTyrtWwEF38AUIyLzCWgomckXwm10I'

# Список инженеров со смещением времени
SHIFT_MINUS_2 = [
    "Ершов Александр ПРМ",
    "Нелюбин Никита ПРМ",
    "Полянцев Евгений ПРМ",
    "Шкаров Иван ПРМ",
    "Раков Роман ПРМ"
]

SHIFT_MINUS_4 = ["Соколов Сергей НСК"]

def show_shift_info(update, context, is_query=False):
    now = datetime.now() - timedelta(hours=2)
    current_hour = now.hour
    current_day = now.day
    previous_day = (now - timedelta(days=1)).day

    try:
        with open("engineers.json", encoding="utf-8") as f:
            data = json.load(f)
            eng_data = data["Инженеры"]
            update_time = data["Время последнего обновления"]

        with open("work_hour.json", encoding="utf-8") as f:
            work_hours = json.load(f)

        with open("telegram_link.json", encoding="utf-8") as f:
            telegram_links = json.load(f)

        with open("departament.json", encoding="utf-8") as f:
            departments = json.load(f)

        message_lines = [
            "👷‍♂️ <b>Сейчас на смене:</b>",
            "🕐 Время всех сотрудников указано по Пермскому времени\n"
        ]

        found = False

        for name, schedule in eng_data.items():
            day_index = current_day - 1
            if len(schedule) <= day_index:
                continue

            value = schedule[day_index]

            # Дополнительная проверка ночной смены
            if current_hour < 8 and isinstance(value, int) and value >= 20:
                day_index = previous_day - 1
                if len(schedule) <= day_index:
                    continue
                value = schedule[day_index]

            if value in ["в", "о"] or not isinstance(value, int):
                continue

            shift_start = value
            if name in SHIFT_MINUS_2:
                shift_start -= 2
            elif name in SHIFT_MINUS_4:
                shift_start -= 4

            shift_mode = work_hours.get(name, 0)
            shift_end = shift_start + (9 if shift_mode == 1 else 12)

            if shift_end >= 24:
                shift_end_display = shift_end % 24
            else:
                shift_end_display = shift_end

            start_str = f"{shift_start % 24:02d}:00"
            shift_end_str = f"{shift_end_display:02d}:00"

            if (shift_start % 24) <= current_hour < (shift_end_display % 24) or \
               (shift_end >= 24 and (current_hour < shift_end_display or current_hour >= shift_start % 24)):
                telegram = telegram_links.get(name, "https://t.me/")
                department = departments.get(name, "❓ Отдел: не указан")
                message_lines.append(
                    f"👤 <b>{name}</b>\n"
                    f"🕒 Смена: <b>{start_str}–{shift_end_str}</b>\n"
                    f"🔗 <a href=\"{telegram}\">Написать</a>\n"
                    f"🏢 Отдел: {department}\n"
                )
                found = True

        if not found:
            message_lines.append("😴 Сейчас никого на смене нет")

        message_lines.append(f"\nОбновлено: <i>{update_time.strip()}</i>")
        message = "\n".join(message_lines)

    except Exception as e:
        message = f"Ошибка при чтении файла: {e}"

    keyboard = [[InlineKeyboardButton("ℹ️ Об этом боте", callback_data='about_bot')]]

    if is_query:
        update.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML', disable_web_page_preview=True)
    else:
        update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML', disable_web_page_preview=True)

def show_about(update, context):
    try:
        with open("about.txt", encoding="utf-8") as f:
            about_text = f.read()
    except Exception as e:
        about_text = f"Ошибка при чтении файла: {e}"

    keyboard = [[InlineKeyboardButton("🔙 В начало", callback_data='main_who')]]
    update.edit_message_text(about_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML', disable_web_page_preview=True)

def start(update: Update, context: CallbackContext):
    show_shift_info(update, context)

def handle_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    query.answer()

    if data == 'about_bot':
        show_about(query, context)

    elif data == 'main_who':
        show_shift_info(query, context, is_query=True)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(handle_buttons))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
