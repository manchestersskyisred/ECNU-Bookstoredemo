import requests
from urllib.parse import urljoin
from fe.access import book
from fe.access.auth import Auth

# 商家类，用于与后端 API 进行交互
class Seller:
    def __init__(self, url_prefix, seller_id: str, password: str):
        # 初始化商家对象，设置接口地址、商家ID、密码等信息
        self.url_prefix = urljoin(url_prefix, "seller/")  # 后端接口的 URL 前缀
        self.seller_id = seller_id  # 商家ID
        self.password = password  # 商家密码
        self.terminal = "my terminal"  # 终端信息
        self.auth = Auth(url_prefix)  # 初始化认证对象
        code, self.token = self.auth.login(self.seller_id, self.password, self.terminal)  # 商家登录获取 token
        assert code == 200  # 确保登录成功

    # 创建商店
    def create_store(self, store_id):
        # 创建商店所需的 JSON 数据
        json = {
            "user_id": self.seller_id,
            "store_id": store_id,
        }
        # 调用后端接口创建商店
        url = urljoin(self.url_prefix, "create_store")
        headers = {"token": self.token}  # 设置请求头中的 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回响应的状态码

    # 添加图书到商店
    def add_book(self, store_id: str, stock_level: int, book_info: book.Book) -> int:
        # 构建添加图书的 JSON 数据
        json = {
            "user_id": self.seller_id,
            "store_id": store_id,
            "book_info": book_info.__dict__,  # 图书信息转换为字典形式
            "stock_level": stock_level,  # 图书库存数量
        }
        # 调用后端接口添加图书
        url = urljoin(self.url_prefix, "add_book")
        headers = {"token": self.token}  # 设置请求头中的 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回响应的状态码

    # 增加图书库存
    def add_stock_level(
        self, seller_id: str, store_id: str, book_id: str, add_stock_num: int
    ) -> int:
        # 构建增加库存的 JSON 数据
        json = {
            "user_id": seller_id,
            "store_id": store_id,
            "book_id": book_id,  # 图书ID
            "add_stock_level": add_stock_num,  # 增加的库存数量
        }
        # 调用后端接口增加库存
        url = urljoin(self.url_prefix, "add_stock_level")
        headers = {"token": self.token}  # 设置请求头中的 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回响应的状态码

    # 发货操作
    def ship_order(self, store_id: str, order_id: str) -> int:
        # 构建发货请求的 JSON 数据
        json = {
            "user_id": self.seller_id,
            "store_id": store_id,
            "order_id": order_id,  # 订单ID
        }
        # 调用后端接口发货
        url = urljoin(self.url_prefix, "ship_order")
        headers = {"token": self.token}  # 设置请求头中的 token
        r = requests.post(url, headers=headers, json=json)  # 发送 POST 请求
        return r.status_code  # 返回响应的状态码
