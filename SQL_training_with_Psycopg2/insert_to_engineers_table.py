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
    # Выполнение SQL-запроса для вставки данных в таблицу
    insert_query = """ 
        INSERT INTO engineers (name) 
        VALUES 
            ('Николаев Дмитрий СПб');           
    """
    cursor.execute(insert_query)
    connection.commit()
    print("запись успешно вставлена")

except (Exception, Error) as error:
    print("Ошибка при работе с PostgreSQL", error)
finally:
    if connection:
        cursor.close()
        connection.close()
        print("Соединение с PostgreSQL закрыто")