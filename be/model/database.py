import logging
import psycopg2


class database:
    database: str

    def __init__(self):
        # self.database = db_info
        self.init_tables()

    def init_tables(self):
        try:
            conn = self.get_db_conn()
            cursor = conn.cursor()

            # 清空表格数据
            cursor.execute(
                "TRUNCATE TABLE new_order_detail, new_order, order_history_detail, order_history, store, user_store, \"user\" RESTART IDENTITY CASCADE")

            # 创建表格结构
            cursor.execute(
                'CREATE TABLE IF NOT EXISTS "user" ('
                'user_id TEXT PRIMARY KEY, password TEXT NOT NULL, '
                'balance INTEGER NOT NULL, token TEXT, terminal TEXT);'
            )

            cursor.execute(
                "CREATE TABLE IF NOT EXISTS user_store("
                "user_id TEXT, store_id TEXT, PRIMARY KEY(user_id, store_id));"
            )

            cursor.execute(
                "CREATE TABLE IF NOT EXISTS store( "
                "store_id TEXT, book_id TEXT, book_info TEXT, stock_level INTEGER,"
                " PRIMARY KEY(store_id, book_id))"
            )

            cursor.execute(
                "CREATE TABLE IF NOT EXISTS new_order( "
                "order_id TEXT PRIMARY KEY, user_id TEXT, store_id TEXT)"
            )

            cursor.execute(
                "CREATE TABLE IF NOT EXISTS new_order_detail( "
                "order_id TEXT, book_id TEXT, count INTEGER, price INTEGER,  "
                "PRIMARY KEY(order_id, book_id))"
            )

            cursor.execute(
                "CREATE TABLE IF NOT EXISTS order_history( "
                "order_id TEXT PRIMARY KEY, user_id TEXT, store_id TEXT, status TEXT)"
            )

            cursor.execute(
                "CREATE TABLE IF NOT EXISTS order_history_detail( "
                "order_id TEXT, book_id TEXT, count INTEGER, price INTEGER,  "
                "PRIMARY KEY(order_id, book_id))"
            )

            cursor.execute(
                "CREATE TABLE IF NOT EXISTS collections( "
                "user_id TEXT, book_id TEXT,  "
                "PRIMARY KEY(user_id, book_id))"
            )
            
            conn.commit()
        except psycopg2.Error as e:
            logging.error(e)
            conn.rollback()
        finally:
            conn.close()
            cursor.close()

    def get_db_conn(self) -> psycopg2.extensions.connection:
        conn = psycopg2.connect(database="bookstore2", user="kerwinlv", password="123456") 
        return conn


database_instance: database = None


def init_database():
    global database_instance
    database_instance = database()


def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()
