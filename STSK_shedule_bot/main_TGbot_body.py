import json
import logging
import os
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters


TOKEN = '7812092497:AAGTfz8AGQCPkkg15SkP3WNDQVFptCTce6k'
PASSWORD = 'stsk'  # Пароль для доступа к боту

#Это нужно для работы модуля логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

special_minus_2 = [
    "Ершов Александр ПРМ",
    "Нелюбин Никита ПРМ",
    "Полянцев Евгений ПРМ",
    "Шкаров Иван ПРМ",
    "Раков Роман ПРМ"
]
special_minus_4 = ["Соколов Сергей НСК"]

months = {
    "01": "Январь", "02": "Февраль", "03": "Март",
    "04": "Апрель", "05": "Май", "06": "Июнь",
    "07": "Июль", "08": "Август", "09": "Сентябрь",
    "10": "Октябрь", "11": "Ноябрь", "12": "Декабрь"
}

engineer_list = []
try:
    with open("work_hour.json", encoding="utf-8") as f:
        work_hours = json.load(f)
        engineer_list = sorted(list(work_hours.keys()))
except:
    pass


def handle_feedback_entry(update: Update, context: CallbackContext):
    if context.user_data.get('waiting_feedback'):
        user = update.effective_user
        text = update.message.text

        feedback_entry = (
            f"Пользователь: {user.username or user.full_name} (ID: {user.id})\n"
            f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Сообщение:\n{text}\n"
            + '-' * 50 + '\n'
        )

        with open("feedback.txt", "a", encoding="utf-8") as f:
            f.write(feedback_entry)

        context.user_data['waiting_feedback'] = False
        update.message.reply_text("✅ Ваше сообщение получено. Спасибо!")
        show_main_menu(update, context)
    else:
        update.message.reply_text("Сначала нажмите кнопку 'Обратная связь'")

def ask_feedback(update, context):
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='main_who')]]
    context.user_data['waiting_feedback'] = True
    update.callback_query.edit_message_text(
        "✏️ Оставьте своё сообщение (без вложений) для автора:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def start(update: Update, context: CallbackContext):
    """Обработчик команды /start - запрашивает пароль"""
    if context.user_data.get('authenticated'):
        show_main_menu(update, context)
    else:
        update.message.reply_text("Добро пожаловать! Введите пароль:")
    user = update.effective_user
    logging.info(f"Пользователь запустил бота: {user.full_name} | @{user.username} | ID: {user.id}")

def handle_password(update: Update, context: CallbackContext):
    if not context.user_data.get('waiting_feedback'):
        if update.message.text == PASSWORD:
            context.user_data['authenticated'] = True
            show_main_menu(update, context)
        else:
            update.message.reply_text("Пароль введен неверно, попробуйте еще раз или запросите у @pasta159")
    else:
        handle_feedback_entry(update, context)

def show_main_menu(update_or_query, context):
    now_utc = datetime.utcnow()
    now_msk = now_utc + timedelta(hours=3)
    current_hour = now_msk.hour
    day_index = now_msk.day - 1
    month = now_msk.strftime("%m")

    weekdays = {
        0: "Понедельник", 1: "Вторник", 2: "Среда",
        3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье"
    }

    months_ru = {
        1: "января", 2: "февраля", 3: "марта",
        4: "апреля", 5: "мая", 6: "июня",
        7: "июля", 8: "августа", 9: "сентября",
        10: "октября", 11: "ноября", 12: "декабря"
    }

    formatted_date = (f"{weekdays[now_msk.weekday()]}, {now_msk.day} "
                      f"{months_ru[now_msk.month]} {now_msk.strftime('%H:%M')}")

    shift_message = generate_shift_message(month, day_index, current_hour)

    message = (f"📅 <b>Текущая дата и время (МСК):</b> {formatted_date}\n"
               f"🕐 Время указано по Московскому времени (UTC+3)\n\n"
               f"👷‍♂️ <b>Сейчас на смене (МСК):</b>\n\n{shift_message}")

    keyboard = [
        [InlineKeyboardButton("📆 Кто работал", callback_data='choose_month')],
        [InlineKeyboardButton("🔎 Смены инженера", callback_data='choose_engineer')],
        [InlineKeyboardButton("ℹ️ О боте", callback_data='about_bot')],
        [InlineKeyboardButton("✉️ Обратная связь", callback_data='feedback')]
    ]

    if isinstance(update_or_query, Update):
        update_or_query.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard),
                                           parse_mode='HTML', disable_web_page_preview=True)
    elif hasattr(update_or_query, 'edit_message_text'):
        update_or_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard),
                                          parse_mode='HTML', disable_web_page_preview=True)
    elif hasattr(update_or_query, 'callback_query') and update_or_query.callback_query:
        update_or_query.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard),
                                                         parse_mode='HTML', disable_web_page_preview=True)

def choose_engineer(update, context):
    keyboard = []
    row = []
    for i, name in enumerate(engineer_list):
        row.append(InlineKeyboardButton(name.split()[0], callback_data=f"engineer_{i}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='main_who')])
    update.callback_query.edit_message_text("Выберите инженера:", reply_markup=InlineKeyboardMarkup(keyboard))

def choose_month_for_engineer(update, context, engineer_index):
    """Выбор месяца для инженера (от января до текущего включительно)"""
    context.user_data['selected_engineer'] = engineer_list[engineer_index]
    current_month = int(datetime.now().strftime("%m"))
    keyboard = []
    row = []

    for month_num in range(1, current_month + 1):
        month_code = f"{month_num:02d}"
        row.append(InlineKeyboardButton(months[month_code], callback_data=f"engmonth_{month_code}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    # Добавляем кнопки навигации
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data='choose_engineer'),
        InlineKeyboardButton("🏠 В начало", callback_data='main_who')
    ])

    update.callback_query.edit_message_text("Выберите месяц:", reply_markup=InlineKeyboardMarkup(keyboard))

def show_engineer_schedule(update, context, month):
    name = context.user_data.get('selected_engineer')
    try:
        with open(os.path.join("schedule_engineers", f"{month}_2025.json"), encoding="utf-8") as f:
            data = json.load(f)
            eng_data = data.get("Инженеры", {})

        if name not in eng_data:
            raise Exception("Инженер не найден в файле")

        days = eng_data[name]
        shift_days = []
        for i, value in enumerate(days):
            if isinstance(value, int):
                shift_days.append(str(i + 1))

        message = f"<b>{name}</b> работал(а) в {months[month]}:\n<b>{', '.join(shift_days) if shift_days else 'Нет смен'}</b>"

    except Exception as e:
        message = f"Ошибка: {e}"

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='choose_engineer')],
                [InlineKeyboardButton("🏠 В начало", callback_data='main_who')]]

    update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

def generate_shift_message(month, day_index, current_hour):
    """Генерирует сообщение о текущих сменах (без заголовков)"""
    try:
        with open(os.path.join("schedule_engineers", f"{month}_2025.json"), encoding="utf-8") as f:
            data = json.load(f)
            eng_data = data["Инженеры"]
            update_time = data.get("Время последнего обновления", "не указано")

        with open("work_hour.json", encoding="utf-8") as f:
            work_hours = json.load(f)

        with open("telegram_link.json", encoding="utf-8") as f:
            telegram_links = json.load(f)

        with open("departament.json", encoding="utf-8") as f:
            departments = json.load(f)

        message_lines = []  # Убрали заголовки из этой функции

        for name, schedule in eng_data.items():
            if len(schedule) <= day_index:
                continue

            value = schedule[day_index]
            if value in ["в", "о"] or not isinstance(value, int):
                continue

            shift_start = value
            if name in special_minus_2:
                shift_start -= 2
            elif name in special_minus_4:
                shift_start -= 4

            shift_mode = work_hours.get(name, 0)
            shift_end = shift_start + (9 if shift_mode == 1 else 12)

            if shift_start <= current_hour < shift_end:
                is_active_shift = True
            elif shift_start >= 20 and current_hour < (shift_end % 24):
                is_active_shift = True
            else:
                is_active_shift = False

            if is_active_shift:
                start_str = f"{shift_start % 24:02d}:00"
                end_str = f"{shift_end % 24:02d}:00"
                telegram = telegram_links.get(name, "https://t.me/")
                department = departments.get(name, "❓ Отдел не указан")

                message_lines.append(
                    f"👤 <b>{name}</b>\n"
                    f"🕒 Смена: <b>{start_str}–{end_str}</b>\n"
                    f"🔗 <a href=\"{telegram}\">Написать</a>\n"
                    f"🏢 Отдел: {department}\n"
                )

        if not message_lines:
            message_lines.append("💤 Сейчас никого нет на смене")

        message_lines.append(f"\nОбновлено: <i>{update_time.strip()}</i>")
        return "\n".join(message_lines)

    except Exception as e:
        return f"⚠️ Ошибка при чтении данных: {e}"

def show_about(update, context):
    try:
        with open("about.txt", encoding="utf-8") as f:
            about_text = f.read()
    except Exception as e:
        about_text = f"Ошибка при чтении файла: {e}"

    keyboard = [[InlineKeyboardButton("🏠 В начало", callback_data='main_who')]]
    update.edit_message_text(about_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

def choose_month(update, context):
    """Показывает месяцы от января до текущего (включительно)"""
    current_month = int(datetime.now().strftime("%m"))
    keyboard = []

    # Создаем кнопки для месяцев от января до текущего
    for month_num in range(1, current_month + 1):
        month_code = f"{month_num:02d}"
        keyboard.append([InlineKeyboardButton(months[month_code], callback_data=f"month_{month_code}")])

    # Добавляем кнопки навигации
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data='main_who'),
        InlineKeyboardButton("🏠 В начало", callback_data='main_who')
    ])

    update.callback_query.edit_message_text("Выберите месяц:", reply_markup=InlineKeyboardMarkup(keyboard))

def choose_day(update, context, month):
    """Выбор дня с учетом только прошедших дней в текущем месяце"""
    current_day = int(datetime.now().strftime("%d"))
    current_month = datetime.now().strftime("%m")
    keyboard = []

    # Определяем сколько дней показывать
    max_day = 31
    if month == current_month:
        max_day = current_day - 1  # Только прошедшие дни

    for day in range(1, max_day + 1):
        if len(keyboard) == 0 or len(keyboard[-1]) == 3:
            keyboard.append([InlineKeyboardButton(str(day), callback_data=f"date_{month}_{day:02d}")])
        else:
            keyboard[-1].append(InlineKeyboardButton(str(day), callback_data=f"date_{month}_{day:02d}"))

    # Добавляем кнопки навигации
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data='choose_month'),
        InlineKeyboardButton("🏠 В начало", callback_data='main_who')
    ])

    update.callback_query.edit_message_text("Выберите день:", reply_markup=InlineKeyboardMarkup(keyboard))

def show_selected_day(update, context, month, day):
    """Показывает кто работал в выбранный день с временем смены"""
    try:
        day_index = int(day) - 1

        with open(os.path.join("schedule_engineers", f"{month}_2025.json"), encoding="utf-8") as f:
            data = json.load(f)
            eng_data = data.get("Инженеры", {})
            update_time = data.get("Время последнего обновления", "не указано")

        with open("work_hour.json", encoding="utf-8") as f:
            work_hours = json.load(f)

        with open("departament.json", encoding="utf-8") as f:
            departments = json.load(f)

        # Собираем всех инженеров, которые работали в этот день
        working_engineers = []
        for name, schedule in eng_data.items():
            if len(schedule) > day_index:
                value = schedule[day_index]
                # Проверяем что значение не "в" и не "о" и является числом
                if value not in ["в", "о"] and isinstance(value, int):
                    # Рассчитываем время смены
                    shift_start = value
                    if name in special_minus_2:
                        shift_start -= 2
                    elif name in special_minus_4:
                        shift_start -= 4

                    shift_mode = work_hours.get(name, 0)
                    shift_end = shift_start + (9 if shift_mode == 1 else 12)

                    start_str = f"{shift_start % 24:02d}:00"
                    end_str = f"{shift_end % 24:02d}:00"
                    department = departments.get(name, "❓ Отдел не указан")

                    working_engineers.append(
                        f"👤 <b>{name}</b>\n"
                        f"🕒 Смена: <b>{start_str}–{end_str}</b>\n"
                        f"🏢 {department}\n"
                    )

        # Формируем сообщение
        month_name = months.get(month, month)
        if working_engineers:
            engineers_list = '\n'.join(working_engineers)
            message = (f"📅 <b>Работали {day}.{month_name}:</b>\n\n" +
                       engineers_list + "\n\n" +
                       f"<i>Обновлено: {update_time.strip()}</i>")
        else:
            message = (f"📅 <b>{day}.{month_name} никто не работал</b>\n\n"
                       f"<i>Обновлено: {update_time.strip()}</i>")

        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data='choose_month')],
            [InlineKeyboardButton("🏠 В начало", callback_data='main_who')]
        ]

        update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML',
            disable_web_page_preview=True
        )

    except Exception as e:
        error_message = f"⚠️ Ошибка при чтении данных: {e}"
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data='choose_month')],
            [InlineKeyboardButton("🏠 В начало", callback_data='main_who')]
        ]
        update.callback_query.edit_message_text(
            error_message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

def handle_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    query.answer()

    if not context.user_data.get('authenticated'):
        query.edit_message_text("Доступ запрещен. Введите /start для авторизации")
        return

    if data == 'about_bot':
        show_about(query, context)
    elif data == 'main_who':
        show_main_menu(query, context)
    elif data == 'choose_month':
        choose_month(update, context)
    elif data.startswith('month_'):
        month = data.split('_')[1]
        choose_day(update, context, month)
    elif data.startswith('date_'):
        _, month, day = data.split('_')
        show_selected_day(update, context, month, day)
    elif data == 'choose_engineer':
        choose_engineer(update, context)
    elif data.startswith('engineer_'):
        index = int(data.split('_')[1])
        choose_month_for_engineer(update, context, index)
    elif data.startswith('engmonth_'):
        month = data.split('_')[1]
        show_engineer_schedule(update, context, month)
    elif data == 'feedback':
        ask_feedback(update, context)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Обработчик команды /start
    dp.add_handler(CommandHandler("start", start))

    # Обработчик пароля (только если не ждем обратную связь)
    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command & ~Filters.regex(r'^/start'),
        handle_password
    ))

    # Обработчик обратной связи
    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command,
        handle_feedback_entry
    ))

    # Обработка кнопок
    dp.add_handler(CallbackQueryHandler(handle_buttons))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()