import psycopg2
from psycopg2 import Error

try:
    # Подключиться к существующей базе данных
    connection = psycopg2.connect(user="postgres",
                                  password="удалено",
                                  host="127.0.0.1",
                                  port="5432",
                                  database="stsk_tg_bot")

    cursor = connection.cursor()
    create_table_query = """ 
        CREATE TABLE IF NOT EXISTS engineer_tg_links (
            id SERIAL PRIMARY KEY,
            engineer_id INTEGER REFERENCES engineers(id),
            tg_link TEXT
        );
    """

    # Выполнение SQL-запроса для вставки данных в таблицу
    insert_query = """ 
        INSERT INTO engineer_tg_links (engineer_id, tg_link) 
        VALUES 
            (12,"https://t.me/dbushin"),
            (13,"https://t.me/lvovgrigory"),
            (14,"https://t.me/aaleksandr_sergeev"),
            (15,"https://t.me/Shapqa12"),
            (16,"https://t.me/CocaHola"),
            (17,"https://t.me/Pasta159"),            
            (18,"https://t.me/Vazhuha"),;                     


    """

    cursor.execute(insert_query)
    cursor.execute(create_table_query)
    connection.commit()
    print("1 запись успешно вставлена")
    # Получить результат
    cursor.execute("SELECT * from departments")
    record = cursor.fetchall()
    print("Результат", record)

# """    # Выполнение SQL-запроса для обновления таблицы
#     update_query = Update mobile set price = 1500 where id = 1
#     cursor.execute(update_query)
#     connection.commit()
#     count = cursor.rowcount
#     print(count, "Запись успешно удалена")
#     # Получить результат
#     cursor.execute("SELECT * from mobile")
#     print("Результат", cursor.fetchall())
#
#
#  # Выполнение SQL-запроса для удаления таблицы
#     delete_query = """Delete from mobile where id = 1"""
#     cursor.execute(delete_query)
#     connection.commit()
#     count = cursor.rowcount
#     print(count, "Запись успешно удалена")
#     # Получить результат
#     cursor.execute("SELECT * from mobile")
#     print("Результат", cursor.fetchall())
# """

except (Exception, Error) as error:
    print("Ошибка при работе с PostgreSQL", error)
finally:
    if connection:
        cursor.close()
        connection.close()
        print("Соединение с PostgreSQL закрыто")