import sqlite3
import pymongo
import os

def load_books(Use_Large_DB: bool):
    ### 读取本地 SQLite 文件 ###
    sqlite_conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), './book_lx.db' if Use_Large_DB else './book.db'))
    sqlite_cursor = sqlite_conn.cursor()

    ### 注释行为本地数据库使用 ###
    mongo_socket = pymongo.MongoClient(os.getenv('MONGODB_API'), server_api=pymongo.server_api.ServerApi('1'))
    # mongo_socket = pymongo.MongoClient('mongodb://localhost:27017')
    db = mongo_socket['bookstore']

    ### 防止重复导入 ###
    if 'books' in db.list_collection_names():
        db.drop_collection('books')
        print(f"Succeed to init collection 'books'.")

    ### 查询 SQLite 数据 ###
    sqlite_cursor.execute('SELECT * FROM book')
    rows = sqlite_cursor.fetchall()

    ### 将数据插入到 MongoDB ###
    for row in rows:
        db['books'].insert_one({
            'id': row[0],
            'title': row[1],
            'author': row[2],
            'publisher': row[3],
            'original_title': row[4],
            'translator': row[5],
            'pub_year': row[6],
            'pages': row[7],
            'price': row[8],
            'currency_unit': row[9],
            'binding': row[10],
            'isbn': row[11],
            'author_intro': row[12],
            'book_intro': row[13],
            'content': row[14],
            'tags': row[15],
            'picture': row[16],
        })

    # 关闭连接
    sqlite_conn.close()
    mongo_socket.close()