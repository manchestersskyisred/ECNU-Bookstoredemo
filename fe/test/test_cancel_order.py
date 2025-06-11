import pytest

from fe.access.buyer import Buyer
from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer
from fe.access.book import Book
import uuid

class TestCancelOrder:
    seller_id: str
    store_id: str
    buyer_id: str
    password: str
    buy_book_info_list: [Book]
    total_price: int
    order_id: str
    buyer: Buyer

    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.seller_id = "test_payment_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_payment_store_id_{}".format(str(uuid.uuid1()))
        self.buyer_id = "test_payment_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = self.seller_id

        b = register_new_buyer(self.buyer_id, self.password)
        self.buyer = b
        gen_book = GenBook(self.seller_id, self.store_id)
        self.buy_book_info_list = []
        self.order_id = []
        for i in range(2):
            ok, buy_book_id_list = gen_book.gen(
                non_exist_book_id=False, low_stock_level=False, max_book_count=1
            )
            self.buy_book_info_list.extend(gen_book.buy_book_info_list)
            assert ok

            code, order_id = b.new_order(self.store_id, buy_book_id_list)
            self.order_id.append(order_id)
            assert code == 200
        self.total_price = 0
        for item in self.buy_book_info_list:
            book: Book = item[0]
            num = item[1]
            if book.price is None:
                continue
            else:
                self.total_price = self.total_price + book.price * num
        self.buyer.add_funds(self.total_price)
        for i in range(1):
            self.buyer.payment(self.order_id[i])
        yield

    def test_ok(self):
        code = self.buyer.cancel_order(self.order_id[1])
        assert code == 200

    def test_wrong_user_id(self):
        self.buyer.user_id = self.buyer.user_id + "_x"
        code = self.buyer.cancel_order(self.order_id[1])
        assert code != 200

    def test_non_exist_order_id(self):
        code = self.buyer.cancel_order(self.order_id[1] + "_x")
        assert code != 200

    def test_repeat_cancel(self):
        code = self.buyer.cancel_order(self.order_id[1])
        assert code == 200
        code = self.buyer.cancel_order(self.order_id[1])
        assert code != 200

    def test_cancel_paid_order(self):
        code = self.buyer.cancel_order(self.order_id[0])
        assert code != 200
