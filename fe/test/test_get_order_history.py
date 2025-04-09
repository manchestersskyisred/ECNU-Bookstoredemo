import pytest

from fe.access.buyer import Buyer
from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer
from fe.access.book import Book

import uuid


class TestGetOrderHistory:
    seller_id: str
    store_id: str
    buyer_id: str
    password: str
    buy_book_info_list: [Book]
    total_price: int
    order_id: [str]
    buyer: Buyer

    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.buyer_id = "test_payment_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = self.buyer_id
        self.buyer = register_new_buyer(self.buyer_id, self.password)

    def test_ok(self):
        code = self.buyer.get_order_history()
        assert code == 200

    def test_non_exist_user_id(self):
        self.buyer.user_id = self.buyer.user_id + "_x"
        code = self.buyer.get_order_history()
        assert code != 200
