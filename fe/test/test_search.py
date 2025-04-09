import pytest
from fe.access.new_seller import register_new_seller
from fe.access import book
from fe.access import auth
from fe import conf
import uuid
import random


class TestSearch:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.auth = auth.Auth(conf.URL)
        self.seller_id = "test_add_books_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_add_books_store_id_{}".format(str(uuid.uuid1()))
        self.password = self.seller_id
        self.seller = register_new_seller(self.seller_id, self.password)

        code = self.seller.create_store(self.store_id)
        assert code == 200
        book_db = book.BookDB()
        self.books = book_db.get_book_info(0, 1)
        for b in self.books:
            code = self.seller.add_book(self.store_id, 0, b)
            assert code == 200
        yield

    def test_search_global(self):
        for b in self.books:
            test_title = b.title
            test_content = b.content.split("\n")[0]
            test_tag = b.tags[random.randint(0,len(b.tags)-1)]
            assert self.auth.search_book(title=test_title) == 200
            assert self.auth.search_book(content=test_content) == 200
            assert self.auth.search_book(tag=test_tag) == 200
            assert self.auth.search_book(title=test_title, content=test_content) == 200
            assert self.auth.search_book(title=test_title, tag=test_tag) == 200
            assert self.auth.search_book(content=test_content, tag=test_tag) == 200
            assert self.auth.search_book(title=test_title, content=test_content, tag=test_tag) == 200

    def test_search_global_not_exists(self):
        test_title = "This is a test title!"
        test_content = "This is a test context!"
        test_tag = "This is a test tag!"
        assert self.auth.search_book(title=test_title) == 529
        assert self.auth.search_book(content=test_content) == 529
        assert self.auth.search_book(tag=test_tag) == 529
        assert self.auth.search_book(title=test_title, content=test_content) == 529
        assert self.auth.search_book(title=test_title, tag=test_tag) == 529
        assert self.auth.search_book(content=test_content, tag=test_tag) == 529
        assert self.auth.search_book(title=test_title, content=test_content, tag=test_tag) == 529

    def test_search_in_store(self):
        for b in self.books:
            test_title = b.title
            test_content = b.content.split("\n")[0]
            test_tag = b.tags[random.randint(0, len(b.tags) - 1)]
            assert self.auth.search_book(title=test_title, store_id=self.store_id) == 200
            assert self.auth.search_book(content=test_content, store_id=self.store_id) == 200
            assert self.auth.search_book(tag=test_tag, store_id=self.store_id) == 200
            assert self.auth.search_book(title=test_title, content=test_content, store_id=self.store_id) == 200
            assert self.auth.search_book(title=test_title, tag=test_tag, store_id=self.store_id) == 200
            assert self.auth.search_book(content=test_content, tag=test_tag, store_id=self.store_id) == 200
            assert self.auth.search_book(title=test_title, content=test_content, tag=test_tag, store_id=self.store_id) == 200

    def test_search_not_exist_store_id(self):
        store_id_not_exist = self.store_id + "_x"
        for b in self.books:
            test_title = b.title
            test_content = b.content.split("\n")[0]
            test_tag = b.tags[random.randint(0, len(b.tags) - 1)]
            assert self.auth.search_book(title=test_title, store_id=store_id_not_exist) == 513
            assert self.auth.search_book(content=test_content, store_id=store_id_not_exist) == 513
            assert self.auth.search_book(tag=test_tag, store_id=store_id_not_exist) == 513
            assert self.auth.search_book(title=test_title, content=test_content, store_id=store_id_not_exist) == 513
            assert self.auth.search_book(title=test_title, tag=test_tag, store_id=store_id_not_exist) == 513
            assert self.auth.search_book(content=test_content, tag=test_tag, store_id=store_id_not_exist) == 513
            assert self.auth.search_book(title=test_title, content=test_content, tag=test_tag,
                                         store_id=store_id_not_exist) == 513

    def test_search_in_store_not_exist(self):
        test_title = "This is a test title!"
        test_content = "This is a test context!"
        test_tag = "This is a test tag!"
        assert self.auth.search_book(title=test_title, store_id=self.store_id) == 529
        assert self.auth.search_book(content=test_content, store_id=self.store_id) == 529
        assert self.auth.search_book(tag=test_tag, store_id=self.store_id) == 529
        assert self.auth.search_book(title=test_title, content=test_content, store_id=self.store_id) == 529
        assert self.auth.search_book(title=test_title, tag=test_tag, store_id=self.store_id) == 529
        assert self.auth.search_book(content=test_content, tag=test_tag, store_id=self.store_id) == 529
        assert self.auth.search_book(title=test_title, content=test_content, tag=test_tag,
                                     store_id=self.store_id) == 529
