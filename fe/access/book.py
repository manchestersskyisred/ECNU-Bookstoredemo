import os
import random
import base64
import pymongo

# 图书类，用于存储图书的相关信息
class Book:
    def __init__(self):
        # 初始化图书的标签和图片列表
        self.tags = []
        self.pictures = []

    # 图书的基本属性
    id: str  # 图书ID
    title: str  # 图书标题
    author: str  # 作者
    publisher: str  # 出版社
    original_title: str  # 原书名
    translator: str  # 译者
    pub_year: str  # 出版年份
    pages: int  # 页数
    price: int  # 价格
    binding: str  # 装帧类型
    isbn: str  # ISBN号
    author_intro: str  # 作者简介
    book_intro: str  # 图书简介
    content: str  # 内容简介
    tags: [str]  # 标签列表
    pictures: [bytes]  # 图书图片列表


# 图书数据库类，负责与数据库的交互
class BookDB:
    __socket = None
    __db = None

    def __init__(self, not_used_param: bool = False):
        # 初始化数据库连接
        ### 注释行专为本地数据库使用 ###
        # 使用环境变量中的 MONGODB_API 连接到 MongoDB 数据库
        self.socket = pymongo.MongoClient(os.getenv('MONGODB_API'), server_api=pymongo.server_api.ServerApi('1'))
        # self.socket = pymongo.MongoClient('mongodb://localhost:27017')  # 也可以直接连接到本地数据库
        self.db = self.socket['bookstore']  # 选择 'bookstore' 数据库

        # 为 'books' 集合的 'id' 字段创建索引，提高查询效率
        try:
            self.db['books'].create_index([("id", pymongo.ASCENDING)])
        except:
            pass  # 如果创建索引失败，忽略错误
        
    # 获取数据库中图书的总数
    def get_book_count(self):
        return self.db['books'].count_documents({})  # 返回 'books' 集合中的文档数

    # 获取指定范围内的图书信息
    def get_book_info(self, start, size) -> [Book]:
        books = []  # 用于存储图书对象的列表
        # 查询 'books' 集合中的数据，跳过前 'start' 条记录，限制返回 'size' 条记录
        cursor = self.db['books'].find().skip(start).limit(size)
        for doc in cursor:
            # 创建一个 Book 对象并赋值
            book = Book()
            book.id = doc.get("id")  # 图书ID
            book.title = doc.get("title")  # 图书标题
            book.author = doc.get("author")  # 作者
            book.publisher = doc.get("publisher")  # 出版社
            book.original_title = doc.get("original_title")  # 原书名
            book.translator = doc.get("translator")  # 译者
            book.pub_year = doc.get("pub_year")  # 出版年份
            book.pages = doc.get("pages")  # 页数
            book.price = doc.get("price")  # 价格

            # 获取其他图书信息
            book.currency_unit = doc.get("currency_unit")  # 货币单位
            book.binding = doc.get("binding")  # 装帧类型
            book.isbn = doc.get("isbn")  # ISBN
            book.author_intro = doc.get("author_intro")  # 作者简介
            book.book_intro = doc.get("book_intro")  # 图书简介
            book.content = doc.get("content")  # 内容简介
            tags = doc.get("tags")  # 图书标签

            # 获取图书的封面图片
            picture = doc.get("picture")

            # 处理标签
            for tag in tags.split("\n"):  # 按换行符分割标签
                if tag.strip() != "":  # 去除空标签
                    book.tags.append(tag)  # 添加标签到标签列表

            # 处理图书图片，将其编码为 base64 字符串并添加到图片列表
            for i in range(0, random.randint(0, 9)):  # 随机生成图片的数量（0到9个）
                if picture is not None:  # 如果有图片
                    encode_str = base64.b64encode(picture).decode("utf-8")  # 将图片进行 base64 编码
                    book.pictures.append(encode_str)  # 添加编码后的图片到图片列表
            
            books.append(book)  # 将图书添加到结果列表
        return books  # 返回查询到的图书列表
