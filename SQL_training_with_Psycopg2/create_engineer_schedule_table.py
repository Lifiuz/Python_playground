import psycopg2
import json
import os
import sys

# Словарь соответствия имен инженеров и их ID
ENGINEER_IDS = {
    "Ершов Александр ПРМ": 1,
    "Нелюбин Никита ПРМ": 2,
    "Кулакова Надежда ПРМ": 3,
    "Полянцев Евгений ПРМ": 4,
    "Соколов Сергей НСК": 5,
    "Шкаров Иван ПРМ": 6,
    "Раков Роман ПРМ": 7,
    "Рыбаков Павел СПб": 8,
    "Кравченко Андрей РНД": 9,
    "Рымарчук Ярослав ПРМ": 10,
    "Кочев Юрий ПРМ": 11,
    "Бушин Дмитрий МСК": 12,
    "Львов Григорий МСК": 13,
    "Сергеев Александр МСК": 14,
    "Попов Павел ПРМ": 15,
    "Сердитов Олег ПРМ": 16,
    "Гафуров Расул ПРМ": 17,
    "Важенин Алексей ЕКБ": 18,
    "Зыбин Сергей СПб": 19,
    "Арсентьев Виталий СПб": 20,
    "Плешаков Александр СПб": 21,
    "Лоскутов Павел ПРМ": 22,
    "Сумин Павел ЕКБ": 23,
    "Куликов Илья СПб": 24,
    "Абсалямова Зарина СПб": 25,
    "Тимохин Евгений СПб": 26,
    "Зверев Сергей СПб": 27,
    "Колегов Владислав СПб": 28,
    "Ольшевская Дарья ПРМ": 29,
    "Сержпинский Роман СПб": 30,
    "Ягодкин Евгений СПб": 31,
    "Приходько Станислав РНД": 32,
    "Фарафонтов Роман ЕКБ": 33,
    "Николаев Дмитрий СПб": 34

}


def main():
    try:
        # Подключение к базе данных
        conn = psycopg2.connect(
            user="postgres",
            password="",
            host="127.0.0.1",
            port="5432",
            database="stsk_tg_bot"
        )
        conn.autocommit = False  # Отключаем авто-коммит для ручного управления транзакциями
        cur = conn.cursor()

        # Создание таблицы (если не существует) в отдельной транзакции
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS engineers_schedule (
                    id SERIAL PRIMARY KEY,
                    engineer_id INTEGER REFERENCES engineers(id),
                    year INTEGER,
                    month INTEGER,
                    day INTEGER,
                    shift_value TEXT
                );
            """)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise Exception(f"Ошибка при создании таблицы: {str(e)}")

        # Начинаем основную транзакцию
        conn.autocommit = False

        # Функция для импорта одного JSON файла
        def import_json_schedule(json_path, year, month):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            engineers = data.get("Инженеры", {})
            for name, shifts in engineers.items():
                engineer_id = ENGINEER_IDS.get(name)
                if engineer_id is None:
                    raise ValueError(f"Инженер '{name}' не найден в списке ID")

                for day, shift in enumerate(shifts, start=1):
                    cur.execute("""
                        INSERT INTO engineers_schedule (engineer_id, year, month, day, shift_value)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (engineer_id, year, month, day, str(shift)))

        # Загрузка данных из всех JSON файлов от 01_2025 до 07_2025
        for month in range(1, 8):
            filename = f"{month:02d}_2025.json"
            if not os.path.exists(filename):
                raise FileNotFoundError(f"Файл не найден: {filename}")

            import_json_schedule(filename, 2025, month)

        # Если все успешно - коммитим изменения
        conn.commit()
        print("Готово: данные загружены в таблицу engineers_schedule.")

    except Exception as e:
        # При любой ошибке откатываем транзакцию
        if 'conn' in locals() and conn:
            conn.rollback()
        print(f"Ошибка: {str(e)}", file=sys.stderr)
        print("Все изменения отменены. Никакие данные не были изменены.", file=sys.stderr)
        sys.exit(1)

    finally:
        # Всегда закрываем соединение
        if 'cur' in locals() and cur:
            cur.close()
        if 'conn' in locals() and conn:
            conn.close()


if __name__ == "__main__":
    main()