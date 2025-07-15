import psycopg2
from psycopg2 import Error

print("-" * 50)
try:
    # Подключиться к существующей базе данных
    connection = psycopg2.connect(user="postgres",
                                  password="удалено",
                                  host="127.0.0.1",
                                  port="5432",
                                  database="stsk_tg_bot")

    cursor = connection.cursor()
    with open("result.csv", "w", encoding="utf-8") as f:
        cursor.copy_expert("""
            COPY (
                SELECT engineer_id, name, tg_link
                FROM engineer_tg_links
                JOIN engineers ON engineer_tg_links.engineer_id = engineers.id
            ) TO STDOUT WITH CSV HEADER
        """, f)

    create_table_query = """ 
        CREATE TABLE IF NOT EXISTS engineer_tg_links  (
            engineer_id INTEGER PRIMARY KEY REFERENCES engineers(id),
            tg_link TEXT
        );
    """

    # Выполнение SQL-запроса для вставки данных в таблицу
    insert_query = """ 
        INSERT INTO engineer_tg_links (engineer_id, tg_link) 
        VALUES 
            (1, 'RSHOVE'),
            (2, 'neliubin_nik'),
            (3, NULL),
            (4, NULL),
            (5, 'QuqAuq'),
            (6, NULL),
            (7, NULL),
            (8, 'MERCSoB'),
            (9, NULL),
            (10, NULL),
            (11, NULL),
            (12, 'dbushin'),
            (13, 'lvovgrigory'),
            (14, 'aaleksandr_sergeev'),
            (15, 'Shapqa12'),
            (16, 'CocaHola'),
            (17, 'Pasta159'),            
            (18, 'Vazhuha'),  
            (19, NULL),
            (20, NULL),
            (21, NULL),
            (22, NULL),
            (23, NULL),
            (24, NULL), 
            (25, NULL),
            (26, NULL),
            (27, NULL),
            (28, NULL),
            (29, NULL),
            (30, NULL),
            (31, NULL),
            (32, NULL),
            (33, NULL),
            (34, NULL);
    """

    cursor.execute(create_table_query)
    cursor.execute(insert_query)
    connection.commit()
    print("успешно")
    print("-" * 50)


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