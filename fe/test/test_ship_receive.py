import pytest

from fe.access.buyer import Buyer
from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer
from fe.access.new_seller import register_new_seller
from fe.access.book import Book
from fe.access.seller import Seller
from fe.conf import Default_User_Funds
import uuid


class TestShipReceive:
    seller_id: str
    store_id: str
    buyer_id: str
    password: str
    buy_book_info_list: [Book]
    total_price: int
    order_id: str
    buyer: Buyer
    seller: Seller

    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.seller_id = "test_payment_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_payment_store_id_{}".format(str(uuid.uuid1()))
        self.buyer_id = "test_payment_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = None
        g = GenBook(self.seller_id, self.store_id)
        self.seller = g.seller
        self.buyer = register_new_buyer(self.buyer_id, self.buyer_id)
        self.buy_book_info_list = []
        self.order_id = None
        
        code, buy_book_id_list = g.gen(non_exist_book_id=False, low_stock_level=False, max_book_count=2)
        assert code == True
        self.buy_book_info_list.extend(g.buy_book_info_list)

        code, self.order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        assert code == 200
        assert self.order_id is not None
        
        yield

    def test_ship_ok(self):
        self.buyer.add_funds(Default_User_Funds)
        self.buyer.payment(self.order_id)
        code = self.seller.ship_order(self.store_id, self.order_id)
        assert code == 200

    def test_receive_ok(self):
        self.buyer.add_funds(Default_User_Funds)
        self.buyer.payment(self.order_id)
        code = self.seller.ship_order(self.store_id, self.order_id)
        assert code == 200
        code = self.buyer.receive_order(self.order_id)
        assert code == 200

    def test_error_store_id(self):
        self.buyer.add_funds(Default_User_Funds)
        self.buyer.payment(self.order_id)
        code = self.seller.ship_order(self.store_id + "_x", self.order_id)
        assert code != 200

    def test_error_order_id(self):
        self.buyer.add_funds(Default_User_Funds)
        self.buyer.payment(self.order_id)
        code = self.seller.ship_order(self.store_id, self.order_id + "_x")
        assert code != 200

    def test_error_seller_id(self):
        self.buyer.add_funds(Default_User_Funds)
        self.buyer.payment(self.order_id)
        self.seller.seller_id = self.seller.seller_id + "_x"
        code = self.seller.ship_order(self.store_id, self.order_id)
        assert code != 200

    def test_error_buyer_id(self):
        self.buyer.add_funds(Default_User_Funds)
        self.buyer.payment(self.order_id)
        code = self.seller.ship_order(self.store_id, self.order_id)
        assert code == 200
        self.buyer.user_id = self.buyer.user_id + "_x"
        code = self.buyer.receive_order(self.order_id)
        assert code != 200

    def test_ship_not_pay(self):
        code = self.seller.ship_order(self.store_id, self.order_id)
        assert code != 200

    def test_receive_not_ship(self):
        code = self.buyer.receive_order(self.order_id)
        assert code != 200

    def test_repeat_ship(self):
        self.buyer.add_funds(Default_User_Funds)
        self.buyer.payment(self.order_id)
        code = self.seller.ship_order(self.store_id, self.order_id)
        assert code == 200
        code = self.seller.ship_order(self.store_id, self.order_id)
        assert code != 200

    def test_repeat_receive(self):
        self.buyer.add_funds(Default_User_Funds)
        self.buyer.payment(self.order_id)
        code = self.seller.ship_order(self.store_id, self.order_id)
        assert code == 200
        code = self.buyer.receive_order(self.order_id)
        assert code == 200
        code = self.buyer.receive_order(self.order_id)
        assert code != 200
