import sqlite3
import pymongo
import os

def load_books(Use_Large_DB: bool):
    ### 读取本地 SQLite 文件 ###
    # 根据是否使用大型数据库来选择读取 book_lx.db 或 book.db
    sqlite_conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), './book_lx.db' if Use_Large_DB else './book.db'))
    sqlite_cursor = sqlite_conn.cursor()

    ### 连接 MongoDB 本地数据库 ###
    # 从环境变量中获取 MongoDB API 地址，连接 MongoDB 数据库
    mongo_socket = pymongo.MongoClient(os.getenv('MONGODB_API'), server_api=pymongo.server_api.ServerApi('1'))
    # mongo_socket = pymongo.MongoClient('mongodb://localhost:27017')  # 也可以直接连接到本地数据库
    db = mongo_socket['bookstore']  # 选择 bookstore 数据库

    ### 防止重复导入数据 ###
    # 如果 MongoDB 中已经存在 'books' 集合，则先删除旧集合，确保不重复导入
    if 'books' in db.list_collection_names():
        db.drop_collection('books')
        print(f"成功初始化集合 'books'.")

    ### 查询 SQLite 数据库中的所有图书数据 ###
    sqlite_cursor.execute('SELECT * FROM book')  # 执行 SQL 查询，获取所有图书数据
    rows = sqlite_cursor.fetchall()  # 获取查询结果

    ### 将查询到的数据插入到 MongoDB ###
    # 遍历所有查询到的行，将每一本书的数据以字典形式插入 MongoDB 中
    for row in rows:
        db['books'].insert_one({
            'id': row[0],  # 图书ID
            'title': row[1],  # 图书标题
            'author': row[2],  # 作者
            'publisher': row[3],  # 出版社
            'original_title': row[4],  # 原书名
            'translator': row[5],  # 译者
            'pub_year': row[6],  # 出版年份
            'pages': row[7],  # 页数
            'price': row[8],  # 价格
            'currency_unit': row[9],  # 货币单位
            'binding': row[10],  # 装帧类型
            'isbn': row[11],  # ISBN
            'author_intro': row[12],  # 作者简介
            'book_intro': row[13],  # 图书简介
            'content': row[14],  # 内容简介
            'tags': row[15],  # 标签
            'picture': row[16],  # 图书封面图片
        })

    # 关闭 SQLite 和 MongoDB 连接
    sqlite_conn.close()  # 关闭 SQLite 连接
    mongo_socket.close()  # 关闭 MongoDB 连接
