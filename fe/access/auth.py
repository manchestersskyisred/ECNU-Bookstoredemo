import requests
from urllib.parse import urljoin


class Auth:
    def __init__(self, url_prefix):
        # 初始化时设置 URL 前缀
        self.url_prefix = urljoin(url_prefix, "auth/")  # 拼接认证相关接口的前缀 URL

    # 用户登录
    def login(self, user_id: str, password: str, terminal: str) -> (int, str):
        # 构建登录请求的 JSON 数据
        payload = {"user_id": user_id, "password": password, "terminal": terminal}
        # 拼接登录接口的完整 URL
        endpoint = urljoin(self.url_prefix, "login")
        # 发送 POST 请求进行登录
        response = requests.post(endpoint, json=payload)
        # 返回响应的状态码和从响应中获取的 token
        return response.status_code, response.json().get("token")

    # 用户注册
    def register(self, user_id: str, password: str) -> int:
        # 构建注册请求的 JSON 数据
        payload = {"user_id": user_id, "password": password}
        # 拼接注册接口的完整 URL
        endpoint = urljoin(self.url_prefix, "register")
        # 发送 POST 请求进行注册
        response = requests.post(endpoint, json=payload)
        # 返回响应的状态码
        return response.status_code

    # 修改密码
    def password(self, user_id: str, old_password: str, new_password: str) -> int:
        # 构建修改密码请求的 JSON 数据
        payload = {
            "user_id": user_id,
            "oldPassword": old_password,
            "newPassword": new_password,
        }
        # 拼接修改密码接口的完整 URL
        endpoint = urljoin(self.url_prefix, "password")
        # 发送 POST 请求进行修改密码
        response = requests.post(endpoint, json=payload)
        # 返回响应的状态码
        return response.status_code

    # 用户登出
    def logout(self, user_id: str, token: str) -> int:
        # 构建登出请求的 JSON 数据
        payload = {"user_id": user_id}
        headers = {"token": token}  # 在请求头中包含 token
        # 拼接登出接口的完整 URL
        endpoint = urljoin(self.url_prefix, "logout")
        # 发送 POST 请求进行登出
        response = requests.post(endpoint, headers=headers, json=payload)
        # 返回响应的状态码
        return response.status_code

    # 用户注销
    def unregister(self, user_id: str, password: str) -> int:
        # 构建注销请求的 JSON 数据
        payload = {"user_id": user_id, "password": password}
        # 拼接注销接口的完整 URL
        endpoint = urljoin(self.url_prefix, "unregister")
        # 发送 POST 请求进行注销
        response = requests.post(endpoint, json=payload)
        # 返回响应的状态码
        return response.status_code

    # 搜索图书
    def search_book(self, title='', content='', tag='', store_id='') -> int:
        # 构建搜索图书请求的 JSON 数据
        payload = {"title": title, "content": content, "tag": tag, "store_id": store_id}
        # 拼接搜索图书接口的完整 URL
        endpoint = urljoin(self.url_prefix, "search_book")
        # 发送 POST 请求进行搜索
        response = requests.post(endpoint, json=payload)
        # 如果没有找到匹配的图书，可以根据需要返回自定义的消息
        # if r.status_code == 529:
        #     return r.status_code, "No matching books found."
        return response.status_code  # 返回响应的状态码
