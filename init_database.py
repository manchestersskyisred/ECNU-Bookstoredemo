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

# 创建表的 SQL 语句
cur.execute(
    'CREATE TABLE IF NOT EXISTS "user" ('
    'user_id TEXT PRIMARY KEY, password TEXT NOT NULL, '
    'balance INTEGER NOT NULL, token TEXT, terminal TEXT);'
)

cur.execute(
    "CREATE TABLE IF NOT EXISTS user_store("
    "user_id TEXT, store_id TEXT, PRIMARY KEY(user_id, store_id));"
)

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

# 提交事务
conn.commit()

# 关闭游标和连接
cur.close()
conn.close(


)