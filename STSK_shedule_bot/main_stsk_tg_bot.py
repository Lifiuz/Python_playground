import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import psycopg2
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters

# Загрузка переменных из .env
load_dotenv()

# Конфигурация
TOKEN = os.getenv("TOKEN")
ENTRY_PASSWORD = os.getenv("ENTRY_PASSWORD")

# Создаём словарь с параметрами подключения из env файла
DB_CONFIG = {
    'dbname': os.getenv("DB_NAME"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'host': os.getenv("DB_HOST"),
    'port': os.getenv("DB_PORT")
}

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# Создаем обработчик для записи в файл
file_handler = logging.FileHandler('log.txt', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
# Добавляем обработчик в корневой логгер
logging.getLogger().addHandler(file_handler)

# Специальные правила для смен (можно хранить в БД, но пока оставим как есть)
special_minus_2 = [1, 2, 4, 6, 7]  # ID инженеров с особым правилом -2 часа
special_minus_4 = [5]  # ID инженера с особым правилом -4 часа

months = {
    "01": "Январь", "02": "Февраль", "03": "Март",
    "04": "Апрель", "05": "Май", "06": "Июнь",
    "07": "Июль", "08": "Август", "09": "Сентябрь",
    "10": "Октябрь", "11": "Ноябрь", "12": "Декабрь"
}

def get_db_connection():
    """Устанавливает соединение с базой данных"""
    return psycopg2.connect(**DB_CONFIG)

def get_engineers_list():
    """Получает список всех инженеров из базы данных"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name FROM engineers ORDER BY name")
            return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

engineer_list = get_engineers_list()

def get_update_time(month):
    """Получает время последнего обновления для указанного месяца"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT refresh_time 
                FROM update_time
                WHERE month = %s
            """, (month,))
            result = cursor.fetchone()
            return result[0].strftime('%Y-%m-%d %H:%M:%S') if result else "не указано"
    except Exception as e:
        logging.error(f"Ошибка при получении времени обновления: {e}")
        return "не указано"
    finally:
        conn.close()

def get_engineer_info(engineer_name):
    """Получает полную информацию об инженере из базы данных"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT e.id, w.smena, d.department_id, t.tg_link
                FROM engineers e
                LEFT JOIN engineer_work_hour w ON e.id = w.engineer_id
                LEFT JOIN engineer_departments d ON e.id = d.engineer_id
                LEFT JOIN engineer_tg_links t ON e.id = t.engineer_id
                WHERE e.name = %s
            """, (engineer_name,))
            result = cursor.fetchone()

            if not result:
                return None

            return {
                'id': result[0],
                'shift_duration': int(result[1]) if result[1] else 12,
                'department_id': result[2],
                'telegram_link': result[3] if result[3] else "https://t.me/"
            }
    finally:
        conn.close()

def get_engineer_schedule(engineer_id, year, month):
    """Получает расписание инженера за указанный месяц"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT day, shift_value 
                FROM engineers_schedule
                WHERE engineer_id = %s AND year = %s AND month = %s
                ORDER BY day
            """, (engineer_id, year, month))
            return cursor.fetchall()
    finally:
        conn.close()

def get_day_schedule(year, month, day):
    """Получает расписание всех инженеров на указанный день"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT e.name, s.shift_value, w.smena, d.department_id
                FROM engineers_schedule s
                JOIN engineers e ON s.engineer_id = e.id
                LEFT JOIN engineer_work_hour w ON e.id = w.engineer_id
                LEFT JOIN engineer_departments d ON e.id = d.engineer_id
                WHERE s.year = %s AND s.month = %s AND s.day = %s
                AND s.shift_value NOT IN ('в', 'о')
            """, (year, month, day))
            return cursor.fetchall()
    finally:
        conn.close()

def get_current_shift_engineers(year, month, day, current_hour):
    """Получает инженеров, которые сейчас на смене"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT e.name, s.shift_value, w.smena, d.department_id, t.tg_link
                FROM engineers_schedule s
                JOIN engineers e ON s.engineer_id = e.id
                LEFT JOIN engineer_work_hour w ON e.id = w.engineer_id
                LEFT JOIN engineer_departments d ON e.id = d.engineer_id
                LEFT JOIN engineer_tg_links t ON e.id = t.engineer_id
                WHERE s.year = %s AND s.month = %s AND s.day = %s
                AND s.shift_value NOT IN ('в', 'о')
            """, (year, month, day))

            working_engineers = []
            for name, shift_value, shift_duration, department_id, tg_link in cursor.fetchall():
                shift_start = int(shift_value)
                # Применяем специальные правила
                cursor.execute("SELECT id FROM engineers WHERE name = %s", (name,))
                engineer_id = cursor.fetchone()[0]

                if engineer_id in special_minus_2:
                    shift_start -= 2
                elif engineer_id in special_minus_4:
                    shift_start -= 4

                shift_duration = int(shift_duration) if shift_duration else 12
                shift_end = shift_start + shift_duration

                # Проверяем, активна ли сейчас смена
                if shift_start <= current_hour < shift_end:
                    is_active_shift = True
                elif shift_start >= 20 and current_hour < (shift_end % 24):
                    is_active_shift = True
                else:
                    is_active_shift = False

                if is_active_shift:
                    working_engineers.append({
                        'name': name,
                        'shift_start': shift_start,
                        'shift_end': shift_end,
                        'department_id': department_id,
                        'telegram_link': tg_link if tg_link else "https://t.me/"
                    })

            return working_engineers
    finally:
        conn.close()

def get_department_name(department_id):
    """Получает название отдела по ID"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name FROM departments WHERE id = %s", (department_id,))
            result = cursor.fetchone()
            return result[0] if result else "❓ Отдел не указан"
    except Exception as e:
        logging.error(f"Ошибка при получении названия отдела: {e}")
        return "❓ Отдел не указан"
    finally:
        conn.close()

def generate_shift_message(month, day_index, current_hour):
    """Генерирует сообщение о текущих сменах (с использованием БД)"""
    try:
        now_utc = datetime.utcnow()
        now_msk = now_utc + timedelta(hours=3)
        year = now_msk.year
        day = now_msk.day

        working_engineers = get_current_shift_engineers(year, month, day, current_hour)
        update_time = get_update_time(int(month))

        message_lines = []
        for engineer in working_engineers:
            start_str = f"{engineer['shift_start'] % 24:02d}:00"
            end_str = f"{engineer['shift_end'] % 24:02d}:00"

            message_lines.append(
                f"👤 <b>{engineer['name']}</b>\n"
                f"🕒 Смена: <b>{start_str}–{end_str}</b>\n"
                f"🔗 <a href=\"{engineer['telegram_link']}\">Написать</a>\n"
                f"🏢 Отдел: {get_department_name(engineer['department_id'])}\n"
            )

        if not message_lines:
            message_lines.append("💤 Сейчас никого нет на смене")

        message_lines.append(f"\nОбновлено: <i>{update_time}</i>")
        return "\n".join(message_lines)

    except Exception as e:
        return f"⚠️ Ошибка при чтении данных: {e}"

def show_main_menu(update_or_query, context):
    """Показывает главное меню бота"""
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
        [InlineKeyboardButton("📆 Поиск по дате", callback_data='choose_month')],
        [InlineKeyboardButton("🔎 Поиск смен по инженеру", callback_data='choose_engineer')],
        [InlineKeyboardButton("ℹ️ О боте", callback_data='about_bot')],
        [InlineKeyboardButton("✉️ Обратная связь", callback_data='feedback')]
    ]

    if isinstance(update_or_query, Update):
        update_or_query.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    elif hasattr(update_or_query, 'edit_message_text'):
        update_or_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    elif hasattr(update_or_query, 'callback_query') and update_or_query.callback_query:
        update_or_query.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML',
            disable_web_page_preview=True
        )

# Обработчик команды /start
def start(update: Update, context: CallbackContext):

    if context.user_data.get('authenticated'):
        show_main_menu(update, context)
    else:
        update.message.reply_text("Добро пожаловать! Введите пароль:")

    user = update.effective_user
    logging.info(f"Пользователь запустил бота: {user.full_name} | @{user.username} | ID: {user.id}")
    # Добавляем запись в лог-файл
    with open('log.txt', 'a', encoding='utf-8') as f:
        f.write(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Пользователь вошёл в бота: {user.full_name} | @{user.username} | ID: {user.id}\n")


def handle_password(update: Update, context: CallbackContext):
    """Обрабатывает введенный пароль"""
    if not context.user_data.get('waiting_feedback'):
        if update.message.text == ENTRY_PASSWORD:
            context.user_data['authenticated'] = True
            show_main_menu(update, context)
        else:
            update.message.reply_text("Пароль введен неверно, попробуйте еще раз или запросите у администратора")
    else:
        handle_feedback_entry(update, context)

def handle_feedback_entry(update: Update, context: CallbackContext):
    """Обрабатывает сообщение обратной связи"""
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
    """Запрашивает обратную связь"""
    try:
        # Читаем содержимое из файла
        with open("ask_feedback.txt", "r", encoding="utf-8") as file:
            feedback_text = file.read().strip()

        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='main_who')]]
        context.user_data['waiting_feedback'] = True

        # Используем прочитанный текст из файла
        update.callback_query.edit_message_text(
            feedback_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'  # Если в тексте есть HTML-форматирование
        )

    except FileNotFoundError:
        update.callback_query.edit_message_text(
            "Не удалось загрузить кнопку обратной связи, попробуйте связаться с @pasta159",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logging.error("Файл ask_feedback.txt не найден")

    except Exception as e:
        update.callback_query.edit_message_text(
            "Произошла ошибка при чтении файла обратной связи",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logging.error(f"Ошибка при чтении файла: {str(e)}")

def choose_engineer(update, context):
    """Показывает список инженеров для выбора"""
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

    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data='choose_engineer'),
        InlineKeyboardButton("🏠 В начало", callback_data='main_who')
    ])

    update.callback_query.edit_message_text("Выберите месяц:", reply_markup=InlineKeyboardMarkup(keyboard))

def choose_month(update, context):
    """Показывает месяцы от января до текущего (включительно)"""
    current_month = int(datetime.now().strftime("%m"))
    keyboard = []

    for month_num in range(1, current_month + 1):
        month_code = f"{month_num:02d}"
        keyboard.append([InlineKeyboardButton(months[month_code], callback_data=f"month_{month_code}")])

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

    max_day = 31
    if month == current_month:
        max_day = current_day - 1

    for day in range(1, max_day + 1):
        if len(keyboard) == 0 or len(keyboard[-1]) == 3:
            keyboard.append([InlineKeyboardButton(str(day), callback_data=f"date_{month}_{day:02d}")])
        else:
            keyboard[-1].append(InlineKeyboardButton(str(day), callback_data=f"date_{month}_{day:02d}"))

    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data='choose_month'),
        InlineKeyboardButton("🏠 В начало", callback_data='main_who')
    ])

    update.callback_query.edit_message_text("Выберите день:", reply_markup=InlineKeyboardMarkup(keyboard))

def show_about(update, context):
    """Показывает информацию о боте из файла about.txt"""
    try:
        with open("about.txt", "r", encoding="utf-8") as f:
            about_text = f.read().strip()

        keyboard = [[InlineKeyboardButton("🏠 В начало", callback_data='main_who')]]
        update.edit_message_text(about_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except FileNotFoundError:
        update.edit_message_text("❗ Файл about.txt не найден.")
    except Exception as e:
        update.edit_message_text(f"⚠️ Ошибка при загрузке информации: {e}")


#Показывает, кто работал в выбранный день
def show_selected_day(update, context, month, day):

    try:
        year = datetime.now().year
        schedule_data = get_day_schedule(year, month, day)
        update_time = get_update_time(int(month))

        working_engineers = []
        for name, shift_value, shift_duration, department_id in schedule_data:
            shift_start = int(shift_value)
            engineer_info = get_engineer_info(name)

            if engineer_info['id'] in special_minus_2:
                shift_start -= 2
            elif engineer_info['id'] in special_minus_4:
                shift_start -= 4

            shift_duration = int(shift_duration) if shift_duration else 12
            shift_end = shift_start + shift_duration

            start_str = f"{shift_start % 24:02d}:00"
            end_str = f"{shift_end % 24:02d}:00"

            working_engineers.append(
                f"👤 <b>{name}</b>\n"
                f"🕒 Смена: <b>{start_str}–{end_str}</b>\n"
                f"🏢 Отдел: {get_department_name(department_id)}\n"
            )

        month_name = months.get(month, month)
        if working_engineers:
            message_parts = [
                f"📅 <b>Работали {day}.{month_name}:</b>",
                "",
                *working_engineers,
                "",
                f"<i>Обновлено: {update_time}</i>"
            ]
            message = "\n".join(message_parts)
        else:
            message = "\n".join([
                f"📅 <b>{day}.{month_name} никто не работал</b>",
                "",
                f"<i>Обновлено: {update_time}</i>"
            ])
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
        error_message = f"⚠️ Ошибка: {str(e)}"
        update.callback_query.edit_message_text(error_message)

#Показывает расписание инженера за месяц
def show_engineer_schedule(update, context, month):

    name = context.user_data.get('selected_engineer')
    try:
        year = datetime.now().year
        engineer_info = get_engineer_info(name)
        if not engineer_info:
            raise Exception("Инженер не найден в базе данных")

        schedule = get_engineer_schedule(engineer_info['id'], year, month)
        update_time = get_update_time(int(month))

        shift_days = [str(day) for day, value in schedule if str(value).isdigit()]

        message = (f"<b>{name}</b> работал(а) в {months[month]}:\n"
                  f"<b>{', '.join(shift_days) if shift_days else 'Нет смен'}</b>\n\n"
                  f"<i>Обновлено: {update_time}</i>")

        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data='choose_engineer')],
            [InlineKeyboardButton("🏠 В начало", callback_data='main_who')]
        ]
        update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        error_message = f"Ошибка: {str(e)}"
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data='choose_engineer')],
            [InlineKeyboardButton("🏠 В начало", callback_data='main_who')]
        ]
        update.callback_query.edit_message_text(
            error_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Обрабатывает нажатия кнопок
def handle_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    query.answer()

    user = update.effective_user
    # Логируем нажатие кнопки
    logging.info(f"Пользователь {user.id} нажал кнопку: {data}")

    # Добавляем запись в лог-файл
    with open('log.txt', 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Пользователь {user.id} нажал кнопку: {data}\n")

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
    """Основная функция запуска бота"""
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command & ~Filters.regex(r'^/start'),
        handle_password
    ))
    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command,
        handle_feedback_entry
    ))
    dp.add_handler(CallbackQueryHandler(handle_buttons))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()