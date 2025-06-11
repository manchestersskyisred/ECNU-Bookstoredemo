import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 连接到默认的 PostgreSQL 数据库
conn = psycopg2.connect(
    dbname='bookstore',
    user='kerwinlv',
    password='123456',
    host='localhost',
    port='5432'
)

# 设置自动提交模式
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

# 创建一个游标对象
cur = conn.cursor()

# 检查 bookstore2 数据库是否存在
cur.execute("SELECT 1 FROM pg_database WHERE datname = 'bookstore2'")
exists = cur.fetchone()

# 如果不存在，则创建 bookstore2 数据库
if not exists:
    cur.execute("CREATE DATABASE bookstore2")

# 关闭游标和连接
cur.close()
conn.close()

# 连接到新创建或已存在的 bookstore2 数据库
conn = psycopg2.connect(
    dbname='bookstore2',
    user='kerwinlv',
    password='123456',
    host='localhost',
    port='5432'
)

# 创建一个新的游标对象
cur = conn.cursor()

# 创建优化后的表结构
# 用户表（优化版本）
cur.execute(
    'CREATE TABLE IF NOT EXISTS "user" ('
    'user_id TEXT PRIMARY KEY, '
    'password TEXT NOT NULL, '
    'balance DECIMAL(10,2) NOT NULL DEFAULT 0, '
    'token TEXT, '
    'terminal TEXT, '
    'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, '
    'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);'
)

# 商店信息表
cur.execute(
    "CREATE TABLE IF NOT EXISTS store_info ("
    "store_id TEXT PRIMARY KEY, "
    "store_name TEXT NOT NULL, "
    "description TEXT, "
    "owner_id TEXT NOT NULL, "
    "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
    "FOREIGN KEY (owner_id) REFERENCES \"user\"(user_id) ON DELETE CASCADE);"
)

# 用户商店关联表（优化版本）
cur.execute(
    "CREATE TABLE IF NOT EXISTS user_store ("
    "user_id TEXT, "
    "store_id TEXT, "
    "role TEXT DEFAULT 'owner', "
    "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
    "PRIMARY KEY(user_id, store_id), "
    "FOREIGN KEY (user_id) REFERENCES \"user\"(user_id) ON DELETE CASCADE, "
    "FOREIGN KEY (store_id) REFERENCES store_info(store_id) ON DELETE CASCADE);"
)

# 书籍目录表
cur.execute(
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

# 商店库存表（替代原store表）
cur.execute(
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

# 统一订单表（替代new_order和order_history）
cur.execute(
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

# 订单详情表
cur.execute(
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

# 用户收藏表（优化版本）
cur.execute(
    "CREATE TABLE IF NOT EXISTS user_favorites ("
    "user_id TEXT, "
    "book_id TEXT, "
    "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
    "PRIMARY KEY(user_id, book_id), "
    "FOREIGN KEY (user_id) REFERENCES \"user\"(user_id) ON DELETE CASCADE, "
    "FOREIGN KEY (book_id) REFERENCES book_catalog(book_id) ON DELETE CASCADE);"
)

# 支付记录表
cur.execute(
    "CREATE TABLE IF NOT EXISTS payment_history ("
    "payment_id TEXT PRIMARY KEY, "
    "order_id TEXT NOT NULL, "
    "amount DECIMAL(10,2) NOT NULL, "
    "payment_method TEXT DEFAULT 'balance', "
    "status TEXT DEFAULT 'completed', "
    "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
    "FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE);"
)

# 库存变动记录表
cur.execute(
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
cur.execute(
    "CREATE TABLE IF NOT EXISTS store( "
    "store_id TEXT, book_id TEXT, book_info TEXT, stock_level INTEGER,"
    " PRIMARY KEY(store_id, book_id))"
)

cur.execute(
    "CREATE TABLE IF NOT EXISTS new_order( "
    "order_id TEXT PRIMARY KEY, user_id TEXT, store_id TEXT)"
)

cur.execute(
    "CREATE TABLE IF NOT EXISTS new_order_detail( "
    "order_id TEXT, book_id TEXT, count INTEGER, price INTEGER,  "
    "PRIMARY KEY(order_id, book_id))"
)

cur.execute(
    "CREATE TABLE IF NOT EXISTS order_history( "
    "order_id TEXT PRIMARY KEY, user_id TEXT, store_id TEXT, status TEXT)"
)

cur.execute(
    "CREATE TABLE IF NOT EXISTS order_history_detail( "
    "order_id TEXT, book_id TEXT, count INTEGER, price INTEGER,  "
    "PRIMARY KEY(order_id, book_id))"
)

cur.execute(
    "CREATE TABLE IF NOT EXISTS collections( "
    "user_id TEXT, book_id TEXT,  "
    "PRIMARY KEY(user_id, book_id))"
)

# 创建性能优化索引
cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_store_id ON orders(store_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_store_inventory_store_id ON store_inventory(store_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_store_inventory_book_id ON store_inventory(book_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_user_token ON \"user\"(token);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_book_catalog_title ON book_catalog(title);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_book_catalog_author ON book_catalog(author);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_history_order_id ON payment_history(order_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_inventory_logs_store_book ON inventory_logs(store_id, book_id);")

# 提交事务
conn.commit()

# 关闭游标和连接
cur.close()
conn.close(


)