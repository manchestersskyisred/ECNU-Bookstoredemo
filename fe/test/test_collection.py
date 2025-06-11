import pytest

from fe.access.new_buyer import register_new_buyer
from fe.access import book
import uuid
from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer


class TestCollection:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.user_id = "test_new_collection_user_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_new_collection_store_id_{}".format(str(uuid.uuid1()))
        self.buyer_id = "test_new_collection_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = self.buyer_id
        self.buyer = register_new_buyer(self.buyer_id, self.password)
        
        book_db = book.BookDB()
        self.books = book_db.get_book_info(0, 2)

        
        yield

    def test_ok(self):
        for b in self.books:
            code = self.buyer.collect_book(b.id)
            assert code == 200

    def test_collect_book(self):
        for b in self.books:
            code = self.buyer.collect_book(b.id)
            assert code == 200

    def test_get_collection(self):
        code = self.buyer.get_collection(self.buyer_id)
        assert code == 200

    def test_uncollect_book(self):
        for b in self.books:
            code = self.buyer.uncollect_book(b.id)
            assert code == 200
