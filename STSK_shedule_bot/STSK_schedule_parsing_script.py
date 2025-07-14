import os
import psycopg2
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

# Авторизация KB
KB_USERNAME = os.getenv("KB_USERNAME")
KB_PASSWORD = os.getenv("KB_PASSWORD")

# Подключение к PostgreSQL с данными из .env
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

print("-" * 50)
print("Открываем kb...")
driver = webdriver.Chrome()

# Функция авторизации на kb
def login(username, password):
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "os_username"))
        )
        driver.find_element(By.ID, "os_username").send_keys(username)
        driver.find_element(By.ID, "os_password").send_keys(password)
        driver.find_element(By.ID, "loginButton").click()
        print("Авторизация выполнена успешно")
    except NoSuchElementException:
        print("Ошибка: поля или кнопка не найдены")
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")

try:
    driver.get('https://kb.ertelecom.ru/pages/viewpage.action?pageId=1027971596')
except:
    print("Не удалось открыть kb, возможно нет доступа или VPN выключен")
    driver.quit()
    exit()

# Авторизация
try:
    login(KB_USERNAME, KB_PASSWORD)
    WebDriverWait(driver, 8).until(EC.url_changes(driver.current_url))
except Exception as e:
    print(f"Произошла ошибка: {str(e)}")

# Ожидаем появления таблицы
try:
    WebDriverWait(driver, 8).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="main-content"]/div[1]/table'))
    )
    print("Страница успешно открылась!\nСейчас будем парсить...")
except Exception as e:
    print("Произошла ошибка при открытии: ", e)

# Парсинг таблицы
table = driver.find_element(By.XPATH, '//*[@id="main-content"]/div[1]/table')
rows = table.find_elements(By.TAG_NAME, 'tr')

keywords = ["МСК", "ПРМ", "ЕКБ", "СПб", "НСК", "РНД"]
engineers_data = {}
engineer_fio = []
engineers_schedule = []
MONTH = 7
YEAR = 2025
now = datetime.now()
formatted_time = now.strftime("%H:%M %d.%m.%y")

with open('debugging.txt', 'w', encoding='utf-8') as debug_file:
    for row in rows:
        if engineer_fio and engineer_fio[0].count(" ") == 2:
            name = engineer_fio[0].strip()
            engineers_data[name] = engineers_schedule
            debug_file.write(f"{name}: {engineers_schedule}\n")
        engineer_fio = []
        engineers_schedule = []
        for cell in row.find_elements(By.TAG_NAME, 'td'):
            text = cell.text.strip()
            if any(k in text for k in keywords):
                engineer_fio.append(text)
            else:
                match text:
                    case "":
                        engineers_schedule.append("в")  # пустая ячейка = выходной
                    case "о" | "?":
                        engineers_schedule.append(text)  # отпуск или вопрос
                    case _ if text.isdigit():
                        engineers_schedule.append(text)  # смена (цифра)

# Подключение к PostgreSQL
try:
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )
    cursor = conn.cursor()

    for name, schedule in engineers_data.items():
        # %s используется в psycopg2 как placeholder (заполнитель), чтобы безопасно подставить переменные в SQL-запрос
        cursor.execute("SELECT id FROM engineers WHERE name = %s", (name,))
        result = cursor.fetchone()
        if result:
            engineer_id = result[0]
            for day, value in enumerate(schedule, start=1):
                # Если запись уже существует по (engineer_id, year, month, day),
                # то обновляем только shift_value (так работает EXCLUDED.*)
                cursor.execute("""
                    INSERT INTO engineers_schedule (engineer_id, year, month, day, shift_value)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (engineer_id, year, month, day)
                    DO UPDATE SET shift_value = EXCLUDED.shift_value; 
                """, (engineer_id, YEAR, MONTH, day, str(value)))
        else:
            print(f"[!] Инженер не найден в БД: {name}")

    cursor.execute("""
        INSERT INTO "update_time" (month, refresh_time)
        VALUES (%s, %s);
        """,(MONTH, now))

    conn.commit()
    print("Данные успешно записаны в базу данных.")
except Exception as e:
    print("Ошибка при работе с базой данных:", e)
finally:
    if conn:
        cursor.close()
        conn.close()

print("Работа скрипта завершена")
print("-" * 50)
driver.quit()
