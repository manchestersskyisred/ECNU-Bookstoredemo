import os
import random
import base64
import pymongo

class Book:
    def __init__(self):
        self.tags = []
        self.pictures = []

    id: str
    title: str
    author: str
    publisher: str
    original_title: str
    translator: str
    pub_year: str
    pages: int
    price: int
    binding: str
    isbn: str
    author_intro: str
    book_intro: str
    content: str
    tags: [str]
    pictures: [bytes]


class BookDB:
    __socket = None
    __db = None

    def __init__(self, not_used_param: bool = False):
        ### 注释行专为本地数据库使用 ###
        self.socket = pymongo.MongoClient(os.getenv('MONGODB_API'), server_api=pymongo.server_api.ServerApi('1'))
        # self.socket = pymongo.MongoClient('mongodb://localhost:27017')
        self.db = self.socket['bookstore']

        try:
            self.db['books'].create_index([("id", pymongo.ASCENDING)])
        except:
            pass
        
    def get_book_count(self):
        return self.db['books'].count_documents({})

    def get_book_info(self, start, size) -> [Book]:
        books = []
        cursor = self.db['books'].find().skip(start).limit(size)
        for doc in cursor:
            book = Book()
            book.id = doc.get("id")
            book.title = doc.get("title")
            book.author = doc.get("author")
            book.publisher = doc.get("publisher")
            book.original_title = doc.get("original_title")
            book.translator = doc.get("translator")
            book.pub_year = doc.get("pub_year")
            book.pages = doc.get("pages")
            book.price = doc.get("price")

            book.currency_unit = doc.get("currency_unit")
            book.binding = doc.get("binding")
            book.isbn = doc.get("isbn")
            book.author_intro = doc.get("author_intro")
            book.book_intro = doc.get("book_intro")
            book.content = doc.get("content")
            tags = doc.get("tags")

            picture = doc.get("picture")

            for tag in tags.split("\n"):
                if tag.strip() != "":
                    book.tags.append(tag)
            for i in range(0, random.randint(0, 9)):
                if picture is not None:
                    encode_str = base64.b64encode(picture).decode("utf-8")
                    book.pictures.append(encode_str)
            books.append(book)
        return books