import json
import psycopg2
from psycopg2 import Error
from datetime import datetime
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

print("-"*50)
print("Открываем kb...")
driver = webdriver.Chrome()

try:
    driver.get('https://kb.ertelecom.ru/pages/viewpage.action?pageId=1027971596')
except:
    print("Не удалось открыть kb, возможно нет доступа или VPN выключен")
    driver.quit()
    exit()

# Функция для загрузки учетных данных из JSON
def load_credentials():
    try:
        with open('credentials.json', 'r') as file:
            credentials = json.load(file)
            return credentials['username'], credentials['password']
    except FileNotFoundError:
        print("Ошибка: файл credentials.json не найден")
        return None, None
    except json.JSONDecodeError:
        print("Ошибка: не удалось прочитать файл credentials.json")
        return None, None
    except KeyError:
        print("Ошибка: в файле credentials.json отсутствуют необходимые поля")
        return None, None

# Функция для заполнения полей авторизации
def login(username, password):
    try:
        # Ожидание появления полей ввода
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "os_username"))
        )

        # Находим элементы по ID
        username_field = driver.find_element(By.ID, "os_username")
        password_field = driver.find_element(By.ID, "os_password")
        login_button = driver.find_element(By.ID, "loginButton")

        # Заполняем поля
        username_field.clear()
        username_field.send_keys(username)

        password_field.clear()
        password_field.send_keys(password)

        # Нажимаем кнопку входа
        login_button.click()

        print("Авторизация выполнена успешно")

    except NoSuchElementException:
        print("Ошибка: поля или кнопка не найдены")
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")


try:
    username, password = load_credentials()

    if username and password:
        # Выполняем авторизацию
        login(username, password)

        # Добавляем ожидание загрузки после авторизации
        WebDriverWait(driver, 8).until(
            EC.url_changes(driver.current_url)
        )
except Exception as e:
    print(f"Критическая ошибка: {str(e)}")

try:
    # Ожидание пока элемент с определенным селектором не станет доступен
    element = WebDriverWait(driver, 8).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="main-content"]/div[1]/table'))
    )
    print("Страница успешно открылась!\nСейчас будем парсить...")
except Exception as e:
    print("Произошла ошибка при открытии: ", e)


# Найти все строки в таблице
table = driver.find_element(By.XPATH, '//*[@id="main-content"]/div[1]/table')
rows = table.find_elements(By.TAG_NAME, 'tr')

# Итерация по строкам и извлечение данных
keywords = ["МСК", "ПРМ", "ЕКБ", "СПб", "НСК", "РНД"] #не будет работать если кто-то поменяет
engineers_schedule = []
engineer_fio = []
all_engineers = []
# Создаем словарь для хранения данных
engineers_data = {}
engineers_counter = 0
current_date = datetime.now().strftime("%H:%M %d-%m-%Y ")

with open ('debugging.txt', 'w', encoding='utf-8') as debuggingTXT:
    for row in rows:
        if engineer_fio:
            if engineer_fio[0].count(" ") == 2:
                # Это просто в блокнот вывожу для самопроверки
                debuggingTXT.write(f"Сотрудник {engineer_fio} \n Работает: {engineers_schedule}\n")
                engineer_name = engineer_fio[0]
                engineers_data[engineer_name] = engineers_schedule
                all_engineers.append(engineer_fio[0])
                engineers_counter += 1
        cells = row.find_elements(By.TAG_NAME, 'td')  # или 'th' для заголовков
        engineers_schedule = []
        engineer_fio = []
        for cell in cells:
            if any(keyword in cell.text for keyword in keywords):
              engineer_fio.append(cell.text)
            if cell.text.isdigit():
                engineers_schedule.append(int(cell.text))
            if cell.text == "":
                engineers_schedule.append("в")
            if cell.text == "о":
                engineers_schedule.append("о")
            if cell.text == "?":
                engineers_schedule.append("?")

try:
    # Подключиться к существующей базе данных
    connection = psycopg2.connect(user="postgres",
                                  password="Lifius!",
                                  host="127.0.0.1",
                                  port="5432",
                                  database="postgres_db")
    cursor = connection.cursor()

# Записываем все данные в JSON файл один раз после завершения цикла
with open('schedule_engineers/07_2025.json', 'w', encoding='utf-8') as engineersJSON:
    # Создаем основной объект, который будет содержать дату и данные
    output_data = {
        "Время последнего обновления": current_date,
        "Инженеры": engineers_data
    }
    # Записываем весь объект в файл
    json.dump(output_data, engineersJSON, ensure_ascii=False)
print("Работа скрипта завершена")
print("-"*50)
driver.quit()  # Закрываем браузер после завершения работы

