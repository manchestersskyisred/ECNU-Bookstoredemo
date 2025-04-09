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
        books = []
        # 将书籍的 ID 和数量封装为字典列表
        for id_count_pair in book_id_and_count:
            books.append({"id": id_count_pair[0], "count": id_count_pair[1]})
        json = {"user_id": self.user_id, "store_id": store_id, "books": books}  # 创建订单的请求数据
        url = urljoin(self.url_prefix, "new_order")  # 请求的 URL
        headers = {"token": self.token}  # 请求头，包含 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        response_json = r.json()  # 获取响应内容
        return r.status_code, response_json.get("order_id")  # 返回状态码和订单ID

    # 支付订单
    def payment(self, order_id: str):
        json = {
            "user_id": self.user_id,
            "password": self.password,
            "order_id": order_id,  # 支付的订单ID
        }
        url = urljoin(self.url_prefix, "payment")  # 请求的 URL
        headers = {"token": self.token}  # 请求头，包含 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回状态码

    # 充值账户余额
    def add_funds(self, add_value: str) -> int:
        json = {
            "user_id": self.user_id,
            "password": self.password,
            "add_value": add_value,  # 充值金额
        }
        url = urljoin(self.url_prefix, "add_funds")  # 请求的 URL
        headers = {"token": self.token}  # 请求头，包含 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回状态码

    # 获取订单历史
    def get_order_history(self) -> int:
        json = {
            "user_id": self.user_id,  # 用户ID
        }
        url = urljoin(self.url_prefix, "get_order_history")  # 请求的 URL
        headers = {"token": self.token}  # 请求头，包含 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回状态码

    # 取消订单
    def cancel_order(self, order_id: str) -> int:
        json = {
            "user_id": self.user_id,
            "order_id": order_id,  # 要取消的订单ID
        }
        url = urljoin(self.url_prefix, "cancel_order")  # 请求的 URL
        headers = {"token": self.token}  # 请求头，包含 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回状态码

    # 确认收货
    def receive_order(self, order_id: str) -> int:
        json = {
            "user_id": self.user_id,
            "order_id": order_id,  # 收货的订单ID
        }
        url = urljoin(self.url_prefix, "receive_order")  # 请求的 URL
        headers = {"token": self.token}  # 请求头，包含 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回状态码

    # 收藏图书
    def collect_book(self, book_id) -> int:
        json = {
            "user_id": self.user_id,
            "book_id": book_id,  # 要收藏的图书ID
        }
        url = urljoin(self.url_prefix, "collect_book")  # 请求的 URL
        headers = {"token": self.token}  # 请求头，包含 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回状态码

    # 获取收藏夹中的图书
    def get_collection(self, user_id) -> int:
        json = {
            "user_id": self.user_id,  # 用户ID
        }
        url = urljoin(self.url_prefix, "get_collection")  # 请求的 URL
        headers = {"token": self.token}  # 请求头，包含 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回状态码

    # 取消收藏图书
    def uncollect_book(self, book_id) -> int:
        json = {
            "user_id": self.user_id,
            "book_id": book_id,  # 要取消收藏的图书ID
        }
        url = urljoin(self.url_prefix, "uncollect_book")  # 请求的 URL
        headers = {"token": self.token}  # 请求头，包含 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回状态码

    # 收藏商店
    def collect_store(self, store_id) -> int:
        json = {
            "user_id": self.user_id,
            "store_id": store_id,  # 要收藏的商店ID
        }
        url = urljoin(self.url_prefix, "collect_store")  # 请求的 URL
        headers = {"token": self.token}  # 请求头，包含 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回状态码

    # 获取商店收藏
    def get_store_collection(self, user_id) -> int:
        json = {
            "user_id": self.user_id,  # 用户ID
        }
        url = urljoin(self.url_prefix, "get_store_collection")  # 请求的 URL
        headers = {"token": self.token}  # 请求头，包含 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回状态码

    # 取消收藏商店
    def uncollect_store(self, store_id) -> int:
        json = {
            "user_id": self.user_id,
            "store_id": store_id,  # 要取消收藏的商店ID
        }
        url = urljoin(self.url_prefix, "uncollect_store")  # 请求的 URL
        headers = {"token": self.token}  # 请求头，包含 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回状态码
