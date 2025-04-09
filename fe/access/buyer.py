import requests
import simplejson
from urllib.parse import urljoin
from fe.access.auth import Auth

# 买家类，用于与后端 API 进行交互
class Buyer:
    def __init__(self, url_prefix, user_id, password):
        # 初始化买家对象，设置接口地址、用户ID、密码等信息
        self.url_prefix = urljoin(url_prefix, "buyer/")  # 后端接口的 URL 前缀
        self.user_id = user_id  # 用户ID
        self.password = password  # 用户密码
        self.token = ""  # 用于存储登录后的 token
        self.terminal = "my terminal"  # 终端信息
        self.auth = Auth(url_prefix)  # 初始化认证对象
        code, self.token = self.auth.login(self.user_id, self.password, self.terminal)  # 登录并获取 token
        assert code == 200  # 确保登录成功

    # 创建新订单
    def new_order(self, store_id: str, book_id_and_count: [(str, int)]) -> (int, str):
        books = [{"id": pair[0], "count": pair[1]} for pair in book_id_and_count]
        payload = {"user_id": self.user_id, "store_id": store_id, "books": books}
        endpoint = urljoin(self.url_prefix, "new_order")
        headers = {"token": self.token}
        response = requests.post(endpoint, headers=headers, json=payload)
        response_data = response.json()
        return response.status_code, response_data.get("order_id")

    # 支付订单
    def payment(self, order_id: str):
        payload = {
            "user_id": self.user_id,
            "password": self.password,
            "order_id": order_id,
        }
        endpoint = urljoin(self.url_prefix, "payment")
        headers = {"token": self.token}
        response = requests.post(endpoint, headers=headers, json=payload)
        return response.status_code

    # 充值账户余额
    def add_funds(self, add_value: str) -> int:
        payload = {
            "user_id": self.user_id,
            "password": self.password,
            "add_value": add_value,
        }
        endpoint = urljoin(self.url_prefix, "add_funds")
        headers = {"token": self.token}
        response = requests.post(endpoint, headers=headers, json=payload)
        return response.status_code

    # 获取订单历史
    def get_order_history(self) -> int:
        payload = {"user_id": self.user_id}
        endpoint = urljoin(self.url_prefix, "get_order_history")
        headers = {"token": self.token}
        response = requests.post(endpoint, headers=headers, json=payload)
        return response.status_code

    # 取消订单
    def cancel_order(self, order_id: str) -> int:
        payload = {
            "user_id": self.user_id,
            "order_id": order_id,
        }
        endpoint = urljoin(self.url_prefix, "cancel_order")
        headers = {"token": self.token}
        response = requests.post(endpoint, headers=headers, json=payload)
        return response.status_code

    # 确认收货
    def receive_order(self, order_id: str) -> int:
        payload = {
            "user_id": self.user_id,
            "order_id": order_id,
        }
        endpoint = urljoin(self.url_prefix, "receive_order")
        headers = {"token": self.token}
        response = requests.post(endpoint, headers=headers, json=payload)
        return response.status_code

    # 收藏图书
    def collect_book(self, book_id) -> int:
        payload = {
            "user_id": self.user_id,
            "book_id": book_id,
        }
        endpoint = urljoin(self.url_prefix, "collect_book")
        headers = {"token": self.token}
        response = requests.post(endpoint, headers=headers, json=payload)
        return response.status_code

    # 获取收藏夹中的图书
    def get_collection(self, user_id) -> int:
        payload = {"user_id": self.user_id}
        endpoint = urljoin(self.url_prefix, "get_collection")
        headers = {"token": self.token}
        response = requests.post(endpoint, headers=headers, json=payload)
        return response.status_code

    # 取消收藏图书
    def uncollect_book(self, book_id) -> int:
        payload = {
            "user_id": self.user_id,
            "book_id": book_id,
        }
        endpoint = urljoin(self.url_prefix, "uncollect_book")
        headers = {"token": self.token}
        response = requests.post(endpoint, headers=headers, json=payload)
        return response.status_code

    # 收藏商店
    def collect_store(self, store_id) -> int:
        payload = {
            "user_id": self.user_id,
            "store_id": store_id,
        }
        endpoint = urljoin(self.url_prefix, "collect_store")
        headers = {"token": self.token}
        response = requests.post(endpoint, headers=headers, json=payload)
        return response.status_code

    # 获取商店收藏
    def get_store_collection(self, user_id) -> int:
        payload = {"user_id": self.user_id}
        endpoint = urljoin(self.url_prefix, "get_store_collection")
        headers = {"token": self.token}
        response = requests.post(endpoint, headers=headers, json=payload)
        return response.status_code

    # 取消收藏商店
    def uncollect_store(self, store_id) -> int:
        payload = {
            "user_id": self.user_id,
            "store_id": store_id,
        }
        endpoint = urljoin(self.url_prefix, "uncollect_store")
        headers = {"token": self.token}
        response = requests.post(endpoint, headers=headers, json=payload)
        return response.status_code
