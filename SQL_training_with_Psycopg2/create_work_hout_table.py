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
        CREATE TABLE IF NOT EXISTS engineer_work_hour (
            engineer_id INTEGER PRIMARY KEY REFERENCES engineers(id),
            smena TEXT
        );
    """

    # Выполнение SQL-запроса для вставки данных в таблицу
    insert_query = """ 
        INSERT INTO engineer_work_hour (engineer_id, smena) 
        VALUES 
            (1,'12'),
            (2,'12'),
            (3,'9'),
            (4,'9'),
            (5,'9'),
            (6,'9'),
            (7,'9'),
            (8,'9'),
            (9,'9'),
            (10,'12'),
            (11,'12'),
            (12,'9'),
            (13,'9'),
            (14,'9'),
            (15,'9'),
            (16,'12'),
            (17,'12'),            
            (18,'12'),  
            (19,'12'),
            (20,'12'),
            (21,'12'),
            (22,'12'),
            (23,'12'),
            (24,'12'), 
            (25,'12'),
            (26,'12');               
    """
    cursor.execute(create_table_query)
    cursor.execute(insert_query)
    connection.commit()
    print("1 запись успешно вставлена")
    # Получить результат
    cursor.execute("SELECT * from departments")
    record = cursor.fetchall()
    print("Результат", record)

except (Exception, Error) as error:
    print("Ошибка при работе с PostgreSQL", error)
finally:
    if connection:
        cursor.close()
        connection.close()
        print("Соединение с PostgreSQL закрыто")