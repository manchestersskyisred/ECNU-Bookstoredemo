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

            # 清空表格数据（保持向后兼容）
            try:
                cursor.execute("TRUNCATE TABLE new_order_detail, new_order, order_history_detail, order_history, store, user_store, \"user\", collections RESTART IDENTITY CASCADE")
            except psycopg2.Error:
                # 如果表不存在，忽略错误
                pass

            # 创建用户表（优化版本）
            cursor.execute(
                'CREATE TABLE IF NOT EXISTS "user" ('
                'user_id TEXT PRIMARY KEY, '
                'password TEXT NOT NULL, '
                'balance DECIMAL(10,2) NOT NULL DEFAULT 0, '
                'token TEXT, '
                'terminal TEXT, '
                'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, '
                'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);'
            )

            # 创建商店信息表
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS store_info ("
                "store_id TEXT PRIMARY KEY, "
                "store_name TEXT NOT NULL, "
                "description TEXT, "
                "owner_id TEXT NOT NULL, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                "FOREIGN KEY (owner_id) REFERENCES \"user\"(user_id) ON DELETE CASCADE);"
            )

            # 创建用户商店关联表（优化版本）
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS user_store ("
                "user_id TEXT, "
                "store_id TEXT, "
                "role TEXT DEFAULT 'owner', "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                "PRIMARY KEY(user_id, store_id), "
                "FOREIGN KEY (user_id) REFERENCES \"user\"(user_id) ON DELETE CASCADE, "
                "FOREIGN KEY (store_id) REFERENCES store_info(store_id) ON DELETE CASCADE);"
            )

            # 创建书籍目录表
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS book_catalog ("
                "book_id TEXT PRIMARY KEY, "
                "title TEXT NOT NULL, "
                "author TEXT, "
                "publisher TEXT, "
                "isbn TEXT, "
                "price DECIMAL(10,2), "
                "category TEXT, "
                "description TEXT, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
            )

            # 创建商店库存表（替代原store表）
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS store_inventory ("
                "store_id TEXT, "
                "book_id TEXT, "
                "stock_level INTEGER NOT NULL DEFAULT 0, "
                "price_override DECIMAL(10,2), "
                "is_active BOOLEAN DEFAULT TRUE, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                "PRIMARY KEY(store_id, book_id), "
                "FOREIGN KEY (store_id) REFERENCES store_info(store_id) ON DELETE CASCADE, "
                "FOREIGN KEY (book_id) REFERENCES book_catalog(book_id) ON DELETE CASCADE);"
            )

            cursor.execute(
                "CREATE TABLE IF NOT EXISTS orders ("
                "order_id TEXT PRIMARY KEY, "
                "user_id TEXT NOT NULL, "
                "store_id TEXT NOT NULL, "
                "status TEXT NOT NULL DEFAULT 'pending', "
                "total_amount DECIMAL(10,2) NOT NULL DEFAULT 0, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                "FOREIGN KEY (user_id) REFERENCES \"user\"(user_id) ON DELETE CASCADE, "
                "FOREIGN KEY (store_id) REFERENCES store_info(store_id) ON DELETE CASCADE);"
            )

            # 创建订单详情表
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS order_items ("
                "order_id TEXT, "
                "book_id TEXT, "
                "quantity INTEGER NOT NULL, "
                "unit_price DECIMAL(10,2) NOT NULL, "
                "subtotal DECIMAL(10,2) NOT NULL, "
                "PRIMARY KEY(order_id, book_id), "
                "FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE, "
                "FOREIGN KEY (book_id) REFERENCES book_catalog(book_id) ON DELETE CASCADE);"
            )

            # 创建用户收藏表（优化版本）
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS user_favorites ("
                "user_id TEXT, "
                "book_id TEXT, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                "PRIMARY KEY(user_id, book_id), "
                "FOREIGN KEY (user_id) REFERENCES \"user\"(user_id) ON DELETE CASCADE, "
                "FOREIGN KEY (book_id) REFERENCES book_catalog(book_id) ON DELETE CASCADE);"
            )

            # 创建支付记录表
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS payment_history ("
                "payment_id TEXT PRIMARY KEY, "
                "order_id TEXT NOT NULL, "
                "amount DECIMAL(10,2) NOT NULL, "
                "payment_method TEXT DEFAULT 'balance', "
                "status TEXT DEFAULT 'completed', "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                "FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE);"
            )

            # 创建库存变动记录表
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS inventory_logs ("
                "log_id SERIAL PRIMARY KEY, "
                "store_id TEXT NOT NULL, "
                "book_id TEXT NOT NULL, "
                "change_type TEXT NOT NULL, "
                "quantity_change INTEGER NOT NULL, "
                "previous_stock INTEGER NOT NULL, "
                "new_stock INTEGER NOT NULL, "
                "reason TEXT, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                "FOREIGN KEY (store_id, book_id) REFERENCES store_inventory(store_id, book_id));"
            )

            # 保持向后兼容：创建原有表结构
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

            # 创建性能优化索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_store_id ON orders(store_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_inventory_store_id ON store_inventory(store_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_inventory_book_id ON store_inventory(book_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_token ON \"user\"(token);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_catalog_title ON book_catalog(title);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_catalog_author ON book_catalog(author);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_history_order_id ON payment_history(order_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_logs_store_book ON inventory_logs(store_id, book_id);")
            
            conn.commit()
        except psycopg2.Error as e:
            logging.error(e)
            if 'conn' in locals():
                conn.rollback()
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

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
