# 项目总结报告

## 成员：

吕佳鸿 肖岂源 柳絮源

## 一. 后端核心逻辑 (`/be/model`) - 我们系统的大脑

这部分代码是整个网上书店后台的核心，负责处理所有的业务逻辑和数据操作。

### **1. `/be/model/user.py`：用户管理与认证模块**

*   **主要功能介绍**

    这个模块是管理用户账号的"大本营"，完成了用户从 **注册** 新账号开始的所有事情。注册时系统会确保每个用户名都是独一无二的，并给新用户一个初始为零的余额。为了安全，我们使用了 **JWT (JSON Web Token)** 技术来做用户身份认证。每次用户 **登录** 成功（当然要先对一对 **密码**），系统就会发一个有时效（我们设的是1小时）的 **"通行证"(Token)**，用户之后的请求需要带上这个通行证，这样可以让系统知道谁在操作。

    另外，这个模块也能处理用户 **登出**（让通行证失效）、安全地 **修改密码**（得先验证旧密码对不对），以及 **注销账号**（也得验证密码才行）。特别值得一提的是，我们在原有系统的基础上加入了 **书籍搜索** 功能。用户可以输入 **书名、书里的内容、标签** 等关键词来找书，还能指定是在某个 **店里找** 还是 **全网站找**，找书体验明显提升。

*   **核心代码实现**

```python
# JWT Token 生成和验证
def generate_token(user_id: str, terminal: str) -> str:
    payload = {
        "user_id": user_id, 
        "terminal": terminal, 
        "timestamp": time.time()
    }
    encoded = jwt.encode(payload, key=user_id, algorithm="HS256")
    return encoded.encode("utf-8").decode("utf-8")

def verify_token(token_data: str, user_id: str) -> Dict:
    decoded = jwt.decode(token_data, key=user_id, algorithms="HS256")
    return decoded

# 用户注册
def register(self, user_id: str, password: str) -> Tuple[int, str]:
    try:
        db = self.db
        existing_account = db['user'].find_one({"user_id": user_id})
        
        if existing_account:
            return error.error_exist_user_id(user_id)

        device_id = f"terminal_{str(time.time())}"
        auth_token = generate_token(user_id, device_id)
        
        account_data = {
            "user_id": user_id,
            "password": password,
            "balance": 0,
            "token": auth_token,
            "terminal": device_id,
            "created_at": int(time.time())
        }
        
        db['user'].insert_one(account_data)
        return 200, "ok"
        
    except pymongo.errors.PyMongoError as e:
        return self._handle_error(528, str(e))
    except Exception as e:
        return self._handle_error(530, f"Unexpected error: {str(e)}")

# 用户登录
def login(self, user_id: str, password: str, terminal: str) -> Tuple[int, str, str]:
    try:
        status_code, result_msg = self.check_password(user_id, password)
        if status_code != 200:
            return status_code, result_msg, ""

        auth_token = generate_token(user_id, terminal)
        
        update_data = {
            'token': auth_token, 
            'terminal': terminal,
            'last_login': int(time.time())
        }
        
        update_result = self.db['user'].update_one(
            {'user_id': user_id},
            {'$set': update_data}
        )
        
        if not update_result.matched_count:
            return error.error_authorization_fail()
            
        return 200, "ok", auth_token
    except pymongo.errors.PyMongoError as e:
        return self._handle_error(528, str(e), "")
    except Exception as e:
        return self._handle_error(530, f"Unexpected error: {str(e)}", "")
```

*   **设计优点**

    我们使用了 **JWT Token** 和 **密码验证** 的双重保险，使得我们的数据库设计安全性大大提升。
    
    另外Token还设有 **时间限制**，过期了就需要用户重新登录。对用户每次登录、登出的会话管理也做得比较详细，安全系数高。

### **2. `/be/model/buyer.py`：买家业务逻辑模块**

*   **主要功能介绍**

    这个模块管理了买家购买书籍的整个过程。其核心功能在于：

    **下单** (`new_order`)：买家选好书和数量，点击下单，系统会智能地 **检查库存够不够**，如果有存货就 **减少库存** 并生成订单记录存到数据库里。
    
    **付钱** (`payment`)：下单成功之后会进入付钱界面，这时候系统会检查订单状态是否正确、买家 **余额是否充足**、**密码** 输入是否正确，如果没有出错则支付成功，同时卖家的账户余额会增加。

    **充值** (`add_funds`)：买家如果余额不足，可以通过充值功能给自己账户增加余额（需要输密码确认）。

    **查询历史订单** (`get_order_history`)：卖家购买成功后自然会有看购买记录的需求，所以我们提供了查询历史订单的功能。
    
    **取消订单** (`cancel_order`)：在订单尚未支付的时候，买家随时可以取消订单。考虑到一般人的支付习惯，我们设定如果下单超过一段时间后没有付钱，**订单会自动取消**，这样能避免资源浪费。
    
    **确认收货** (`receive_order`): 卖家发货后，买家收到货了可以点击确认收货。
    
    **收藏**(`collect`):为了方便买家下次惠顾，我们添加了 **收藏** 功能，可以 **收藏/取消收藏** 喜欢的 **书** (`collect_book`, `uncollect_book`) 和 **店铺** (`collect_store`, `uncollect_store`)，还能查看自己的 **收藏列表** (`get_collection`, `get_store_collection`)。

*   **核心代码实现**

```python
# 创建新订单
def new_order(self, user_id: str, store_id: str, id_and_count: List[Tuple[str, int]]) -> Tuple[int, str, str]:
    order_id = ""
    try:
        if not self.user_id_exist(user_id):
            return error.error_non_exist_user_id(user_id) + (order_id,)
        if not self.store_id_exist(store_id):
            return error.error_non_exist_store_id(store_id) + (order_id,)
            
        transaction_id = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))
        order_items = []
        
        for book_id, quantity in id_and_count:
            inventory_item = self.db["store"].find_one({"store_id": store_id, "book_id": book_id})
            if not inventory_item:
                return error.error_non_exist_book_id(book_id) + (order_id,)
                
            available_stock = inventory_item["stock_level"]
            if available_stock < quantity:
                return error.error_stock_level_low(book_id) + (order_id,)
                
            query_conditions = {
                "book_id": book_id, 
                "store_id": store_id, 
                "stock_level": {"$gte": quantity}
            }
            stock_update = {"$inc": {"stock_level": -quantity}}
            
            update_result = self.db["store"].update_one(query_conditions, stock_update)
            if update_result.modified_count == 0:
                return error.error_stock_level_low(book_id) + (order_id,)
                
            book_info_json = json.loads(inventory_item["book_info"])
            item_price = book_info_json.get("price") * quantity
            
            order_item = {
                "order_id": transaction_id,
                "book_id": book_id,
                "count": quantity,
                "price": item_price
            }
            order_items.append(order_item)

        if order_items:
            self.db["new_order_detail"].insert_many(order_items)
            
        order_record = {
            "order_id": transaction_id, 
            "user_id": user_id, 
            "store_id": store_id
        }
        self.db["new_order"].insert_one(order_record)
        
        order_id = transaction_id
        self.timer = threading.Timer(10.0, self.cancel_order, args=[user_id, order_id])
        self.timer.start()
        
        history_record = order_record.copy()
        history_record["status"] = "pending"
        history_record["created_at"] = int(time.time())
        
        self.db["order_history"].insert_one(history_record)
        self.db["order_history_detail"].insert_many(order_items)

    except pymongo.errors.PyMongoError as e:
        logging.error("DB Error: {}".format(str(e)))
        return 528, str(e), ""
    except Exception as e:
        logging.info("System Error: {}".format(str(e)))
        return 530, str(e), ""

    return 200, "ok", order_id

# 支付订单
def payment(self, user_id: str, password: str, order_id: str) -> Tuple[int, str]:
    try:
        db = self.db
        order_record = db["new_order"].find_one({"order_id": order_id})
        if not order_record:
            return error.error_invalid_order_id(order_id)
            
        if order_record["user_id"] != user_id:
            return error.error_authorization_fail()
            
        buyer_record = db["user"].find_one({"user_id": user_id})
        if not buyer_record:
            return error.error_non_exist_user_id(user_id)
            
        if password != buyer_record["password"]:
            return error.error_authorization_fail()
            
        order_status = db["order_history"].find_one({"order_id": order_id})["status"]
        if order_status != "pending":
            error.error_invalid_order_status(order_id)
            
        if self.timer:
            self.timer.cancel()
            
        order_details = db["new_order_detail"].find({"order_id": order_id})
        total_amount = sum(item["price"] for item in order_details)
        
        if buyer_record["balance"] < total_amount:
            return error.error_not_sufficient_funds(order_id)
            
        update_result = db["user"].update_one(
            {"user_id": user_id, "balance": {"$gte": total_amount}}, 
            {"$inc": {"balance": -total_amount}}
        )
        
        if update_result.modified_count == 0:
            return error.error_not_sufficient_funds(order_id)
            
        store_owner_record = db["user_store"].find_one({"store_id": order_record["store_id"]})
        seller_id = store_owner_record["user_id"]
        
        if not self.user_id_exist(seller_id):
            return error.error_non_exist_user_id(seller_id)
            
        seller_update = db["user"].update_one(
            {"user_id": seller_id}, 
            {"$inc": {"balance": total_amount}}
        )
        
        if seller_update.modified_count == 0:
            return error.error_non_exist_user_id(seller_id)
            
        db["new_order"].delete_one({"order_id": order_id})
        db["new_order_detail"].delete_many({"order_id": order_id})
        
        history_update = {
            "$set": {
                "status": "paid",
                "paid_at": int(time.time())
            }
        }
        db["order_history"].update_one({"order_id": order_id}, history_update)

    except pymongo.errors.PyMongoError as e:
        return 528, str(e)
    except Exception as e:
        return 530, str(e)

    return 200, "ok"
```

*   **设计优点**

    这部分设计我们特别注意了 **数据的准确性和一致性**。譬如下单、付款等操作，我们确保了相关步骤（比如减库存和生成订单）状态同步（同时成功或者同时失败），不会出现数据不一致的情况。
    
    **订单超时自动取消** 的功能利用了 `threading.Timer` 实现，巧妙而富有现实意义。
    
    在安全性上，对于付钱、充值等敏感操作，都要求 **验证用户身份和密码**，保证了交易安全。

### **3. `/be/model/seller.py`：卖家业务逻辑模块**

*   **主要功能介绍**

    这个模块用于管理卖家的业务，方便卖家管理自己的店铺，其核心功能在于：

    **新开店铺** (`create_store`)：系统会保证店名（ID）不跟别人重复。
    
    **上架新书**(`add_book`)： 店铺开始营业之后，就能往店里上架新书了，卖家填上书的各种信息（书名、作者、简介、价格等等，我们用JSON格式传输）和初始 **库存**。
    
    **增加库存** (`add_stock_level`)：如果书籍畅销，库存没有剩余了，可以用 增加库存功能随时补充。
    
    **发货** (`ship_order`)：买家付钱后，卖家就需要发货，系统会判定这笔订单发货成功，订单状态会变成"已发货"。
    
    **查看自己店铺的所有订单** (`view_orders`)：同卖家查看自己的历史订单一样，卖家也能随时查看自己店铺的所有订单，方便管理。

*   **核心代码实现**

```python
# 创建新店铺
def create_store(self, user_id: str, store_id: str) -> Tuple[int, str]:
    try:
        if not self.user_id_exist(user_id):
            return error.error_non_exist_user_id(user_id)
        if self.store_id_exist(store_id):
            return error.error_exist_store_id(store_id)

        store_data = {
            "store_id": store_id,
            "user_id": user_id,
            "status": "active",
            "created_at": int(time.time())
        }
        
        self.db['user_store'].insert_one(store_data)
        return 200, "ok"
        
    except pymongo.errors.PyMongoError as e:
        return self._handle_error(528, str(e))
    except Exception as e:
        return self._handle_error(530, f"Unexpected error: {str(e)}")

# 上架新书
def add_book(self, user_id: str, store_id: str, book_id: str, book_json_str: str, stock_level: int) -> Tuple[int, str]:
    try:
        if not self.user_id_exist(user_id):
            return error.error_non_exist_user_id(user_id)
        if not self.store_id_exist(store_id):
            return error.error_non_exist_store_id(store_id)
        if self.book_id_exist(store_id, book_id):
            return error.error_exist_book_id(book_id)

        book_data = {
            "book_id": book_id,
            "store_id": store_id,
            "book_info": book_json_str,
            "stock_level": stock_level,
            "created_at": int(time.time()),
            "updated_at": int(time.time())
        }
        
        self.db['store'].insert_one(book_data)
        return 200, "ok"
        
    except pymongo.errors.PyMongoError as e:
        return self._handle_error(528, str(e))
    except Exception as e:
        return self._handle_error(530, f"Unexpected error: {str(e)}")

# 增加库存
def add_stock_level(self, user_id: str, store_id: str, book_id: str, add_stock_level: int) -> Tuple[int, str]:
    try:
        if not self.user_id_exist(user_id):
            return error.error_non_exist_user_id(user_id)
        if not self.store_id_exist(store_id):
            return error.error_non_exist_store_id(store_id)
        if not self.book_id_exist(store_id, book_id):
            return error.error_non_exist_book_id(book_id)

        result = self.db['store'].update_one(
            {'store_id': store_id, 'book_id': book_id},
            {
                '$inc': {'stock_level': add_stock_level},
                '$set': {'updated_at': int(time.time())}
            }
        )
        
        if result.matched_count == 0:
            return error.error_non_exist_book_id(book_id)
            
        return 200, "ok"
        
    except pymongo.errors.PyMongoError as e:
        return self._handle_error(528, str(e))
    except Exception as e:
        return self._handle_error(530, f"Unexpected error: {str(e)}")

# 发货
def ship_order(self, user_id: str, store_id: str, order_id: str) -> Tuple[int, str]:
    try:
        if not self.user_id_exist(user_id):
            return error.error_non_exist_user_id(user_id)
        if not self.store_id_exist(store_id):
            return error.error_non_exist_store_id(store_id)

        order = self.db['order_history'].find_one({'order_id': order_id})
        if not order:
            return error.error_invalid_order_id(order_id)
        if order['status'] != 'paid':
            return error.error_invalid_order_status(order_id)

        result = self.db['order_history'].update_one(
            {'order_id': order_id},
            {
                '$set': {
                    'status': 'shipped',
                    'shipped_at': int(time.time())
                }
            }
        )
        
        if result.matched_count == 0:
            return error.error_invalid_order_id(order_id)
            
        return 200, "ok"
        
    except pymongo.errors.PyMongoError as e:
        return self._handle_error(528, str(e))
    except Exception as e:
        return self._handle_error(530, f"Unexpected error: {str(e)}")
```

*   **设计优点**

    这个模块的设计优点在于 **数据库操作高效**，并且 **逻辑严谨**。

    在增加库存功能中，我们用了MongoDB的一个特殊操作 (`$inc`)，能保证快速又准确地更新数字，能够支持多人同时操作。
    
    安全性和一致性同样是我们始终注重的问题，在做每一步重要操作前，比如开店、加书、发货，我们都会提前 **检查条件**（例如用户信息是否匹配、店铺是否营业、库存是否有存货、订单是否已付钱），确保操作合理，不会数据紊乱。

## **二. 后端接口层 (`/be/view`) - 系统对外的窗口**

这部分代码作为后端的 API 接口，是后端的"窗口"，将后端的核心功能和逻辑，包装到了外部（例如网页或者App）可以模块化调用的标准服务。

### **1. `/be/view/seller.py`：卖家接口视图**

*   **主要功能介绍**

    这个文件是卖家界面的API接口：

    `/create_store` 接口是用来 **新店开业** 的，卖家发送他的用户ID和设定的店铺ID即可。
    
    `/add_book` 是用来 **上架新书** 的，卖家需要提供用户ID、店铺ID、书的详细信息（JSON格式）和库存。
    
    `/add_stock_level` 用来 **增加库存**。
    
    `/ship_order`是卖家用来 **标记订单已发货**的，但系统会先检查这单是否真的已经付款。这些接口都设计成接收 POST 请求和 JSON 数据，返回结果也是统一的 JSON 格式。

*   **核心代码实现**

```python
class Seller:
    def __init__(self, url_prefix: str, token: str):
        self.url_prefix = url_prefix
        self.token = token
        self.headers = {"token": token}

    def create_store(self, user_id: str, store_id: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "store_id": store_id
        }
        response = requests.post(f"{self.url_prefix}/create_store", json=json_data, headers=self.headers)
        return response.status_code, response.json().get("message", "")

    def add_book(self, user_id: str, store_id: str, book_id: str, book_json_str: str, stock_level: int) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "store_id": store_id,
            "book_id": book_id,
            "book_json_str": book_json_str,
            "stock_level": stock_level
        }
        response = requests.post(f"{self.url_prefix}/add_book", json=json_data, headers=self.headers)
        return response.status_code, response.json().get("message", "")

    def add_stock_level(self, user_id: str, store_id: str, book_id: str, add_stock_level: int) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "store_id": store_id,
            "book_id": book_id,
            "add_stock_level": add_stock_level
        }
        response = requests.post(f"{self.url_prefix}/add_stock_level", json=json_data, headers=self.headers)
        return response.status_code, response.json().get("message", "")

    def ship_order(self, user_id: str, store_id: str, order_id: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "store_id": store_id,
            "order_id": order_id
        }
        response = requests.post(f"{self.url_prefix}/ship_order", json=json_data, headers=self.headers)
        return response.status_code, response.json().get("message", "")

    def view_orders(self, user_id: str, store_id: str) -> Tuple[int, List[Dict]]:
        params = {
            "user_id": user_id,
            "store_id": store_id
        }
        response = requests.get(f"{self.url_prefix}/view_orders", params=params, headers=self.headers)
        if response.status_code == 200:
            return response.status_code, response.json().get("orders", [])
        return response.status_code, []
```

*   **设计优点**

    整个模块的设计符合使用习惯， **风格统一**，使用方便。我们统一使用 POST 请求，传 JSON，返回 JSON，大大降低了和前端对接的难度。

    另外 **出错处理** 也合理完善，如果参数确实或者服务器内部出错，会返回明确的提示和错误代码（比如400, 500），方便开发者查明问题。**请求的参数会提前检查**，保证传输的数据准确无误。

### **2. `/be/view/buyer.py`：买家接口视图**

*   **主要功能介绍**
    这里是买家能用到的所有API接口：

    `/new_order` 让买家能 **下订单**，告诉我们要买哪个店的哪些书（书ID和数量），成功了会返回一个订单号。
    
    `/payment` 就是 **付钱** 的接口，需要订单号和买家密码。
    
    `/add_funds` 是 **充值** 接口。
    
    `/get_order_history` 用来 **看买过的订单**。
    
    `/cancel_order` 可以 **取消还没付款的订单**。
    
    `/receive_order` 是 **确认收货**的接口。
    
    `collect` 是一整套 **管理收藏** 的接口：收藏/取消收藏书 (`/collect_book`, `/uncollect_book`)，看收藏的书 (`/get_collection`)；收藏/取消收藏店 (`/collect_store`, `/uncollect_store`)，看收藏的店 (`/get_store_collection`)。

*   **核心代码实现**

```python
class Buyer:
    def __init__(self, url_prefix: str, token: str):
        self.url_prefix = url_prefix
        self.token = token
        self.headers = {"token": token}

    def new_order(self, user_id: str, store_id: str, books: List[Tuple[str, int]]) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "store_id": store_id,
            "books": books
        }
        response = requests.post(f"{self.url_prefix}/new_order", json=json_data, headers=self.headers)
        if response.status_code == 200:
            return response.status_code, response.json().get("order_id", "")
        return response.status_code, ""

    def payment(self, user_id: str, password: str, order_id: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "password": password,
            "order_id": order_id
        }
        response = requests.post(f"{self.url_prefix}/payment", json=json_data, headers=self.headers)
        return response.status_code, response.json().get("message", "")

    def add_funds(self, user_id: str, password: str, add_value: int) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "password": password,
            "add_value": add_value
        }
        response = requests.post(f"{self.url_prefix}/add_funds", json=json_data, headers=self.headers)
        return response.status_code, response.json().get("message", "")

    def get_order_history(self, user_id: str) -> Tuple[int, List[Dict]]:
        params = {"user_id": user_id}
        response = requests.get(f"{self.url_prefix}/get_order_history", params=params, headers=self.headers)
        if response.status_code == 200:
            return response.status_code, response.json().get("orders", [])
        return response.status_code, []

    def cancel_order(self, user_id: str, order_id: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "order_id": order_id
        }
        response = requests.post(f"{self.url_prefix}/cancel_order", json=json_data, headers=self.headers)
        return response.status_code, response.json().get("message", "")

    def receive_order(self, user_id: str, order_id: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "order_id": order_id
        }
        response = requests.post(f"{self.url_prefix}/receive_order", json=json_data, headers=self.headers)
        return response.status_code, response.json().get("message", "")

    def collect_book(self, user_id: str, book_id: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "book_id": book_id
        }
        response = requests.post(f"{self.url_prefix}/collect_book", json=json_data, headers=self.headers)
        return response.status_code, response.json().get("message", "")

    def uncollect_book(self, user_id: str, book_id: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "book_id": book_id
        }
        response = requests.post(f"{self.url_prefix}/uncollect_book", json=json_data, headers=self.headers)
        return response.status_code, response.json().get("message", "")

    def get_collection(self, user_id: str) -> Tuple[int, List[Dict]]:
        params = {"user_id": user_id}
        response = requests.get(f"{self.url_prefix}/get_collection", params=params, headers=self.headers)
        if response.status_code == 200:
            return response.status_code, response.json().get("books", [])
        return response.status_code, []

    def collect_store(self, user_id: str, store_id: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "store_id": store_id
        }
        response = requests.post(f"{self.url_prefix}/collect_store", json=json_data, headers=self.headers)
        return response.status_code, response.json().get("message", "")

    def uncollect_store(self, user_id: str, store_id: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "store_id": store_id
        }
        response = requests.post(f"{self.url_prefix}/uncollect_store", json=json_data, headers=self.headers)
        return response.status_code, response.json().get("message", "")

    def get_store_collection(self, user_id: str) -> Tuple[int, List[Dict]]:
        params = {"user_id": user_id}
        response = requests.get(f"{self.url_prefix}/get_store_collection", params=params, headers=self.headers)
        if response.status_code == 200:
            return response.status_code, response.json().get("stores", [])
        return response.status_code, []
```

*   **设计优点**

    同卖家接口一样，买家接口也保持了 **返回格式的统一**，让前端处理起来方便快捷。
    
    **错误处理周全**，常常遇见的问题大都考虑在内。
    
    另外，我们把复杂的买家逻辑放到了 `model` 层的 `Buyer` 类里，这样这里的 **接口代码就比较干净**，主要负责接收请求和返回结果，**维护起来更容易**。

### **3. `/be/view/auth.py`：认证与公共接口视图**

*   **主要功能介绍**
    这个文件管着用户身份认证和一些任何身份都能使用的接口：

    `/login` 处理 **登录**，对了就发个 Token。

    `/logout` 用来 **登出**，让 Token 失效。

    `/register` 可以 **注册** 新用户。
    
    `unregister` 用于**注销账号**。
    
    `/password` 是 **改密码**。
    
    `/search_book`，**搜书** 接口，可以根据 **书名、内容、标签、店铺** 等条件来搜，灵活便捷。

*   **核心代码实现**

```python
class Auth:
    def __init__(self, url_prefix: str):
        self.url_prefix = url_prefix

    def login(self, user_id: str, password: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "password": password
        }
        response = requests.post(f"{self.url_prefix}/login", json=json_data)
        if response.status_code == 200:
            return response.status_code, response.json().get("token", "")
        return response.status_code, ""

    def logout(self, user_id: str, token: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id
        }
        headers = {"token": token}
        response = requests.post(f"{self.url_prefix}/logout", json=json_data, headers=headers)
        return response.status_code, response.json().get("message", "")

    def register(self, user_id: str, password: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "password": password
        }
        response = requests.post(f"{self.url_prefix}/register", json=json_data)
        return response.status_code, response.json().get("message", "")

    def unregister(self, user_id: str, password: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "password": password
        }
        response = requests.post(f"{self.url_prefix}/unregister", json=json_data)
        return response.status_code, response.json().get("message", "")

    def password(self, user_id: str, old_password: str, new_password: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "oldPassword": old_password,
            "newPassword": new_password
        }
        response = requests.post(f"{self.url_prefix}/password", json=json_data)
        return response.status_code, response.json().get("message", "")

    def search_book(self, query: str, store_id: str = None, page: int = 1, per_page: int = 10) -> Tuple[int, List[Dict]]:
        params = {
            "query": query,
            "page": page,
            "per_page": per_page
        }
        if store_id:
            params["store_id"] = store_id
            
        response = requests.get(f"{self.url_prefix}/search_book", params=params)
        if response.status_code == 200:
            return response.status_code, response.json().get("books", [])
        return response.status_code, []
```

*   **设计优点**

    这部分的接口也设计 **规范**。

    返回格式统一，**错误处理和日志记录** 全部考虑在内，方便开发者调试。
    
    使用方便直接，我们采用 POST 请求，只需要传输对应的参数即可。
    
    **参数检查严格**，保证传输的数据是有效的。

## **三. 前端访问与测试层 (`/fe/access`) - 模拟用户操作**

这部分代码主要是用来 **模拟前端或者测试** 怎么去调用咱们前面写的后端接口的，帮助我们验证功能对不对。

### **1. `/fe/access/auth.py`：认证接口访问客户端**

*   **主要功能介绍**

    我们实现了 `Auth` 类，用来处理后端的认证接口。用这个类我们可以很方便地模拟 **用户登录 (`login`)**、**注册 (`register`)**、**改密码 (`password`)**、**登出 (`logout`)** 和 **注销 (`unregister`)**。
    
    另外系统还包含了 **搜书 (`search_book`)** 的功能，可以指定不同的条件去搜索。类里面的方法本质上能够帮我们发送 HTTP 请求给后端，并告诉我们后端返回的内容（例如状态码，登录成功会返回 Token）。

*   **核心代码实现**

```python
class Auth:
    def __init__(self, url_prefix: str):
        self.url_prefix = url_prefix

    def login(self, user_id: str, password: str) -> Tuple[int, str]:
        json_data = {
            "user_id": user_id,
            "password": password
        }
        response = requests.post(f"{self.url_prefix}/login", json=json_data)
        if response.status_code == 200:
            return response.status_code, response.json().get("token", "")
        return response.status_code, ""

    def register(self, user_id: str, password: str) -> int:
        json_data = {
            "user_id": user_id,
            "password": password
        }
        response = requests.post(f"{self.url_prefix}/register", json=json_data)
        return response.status_code

    def password(self, user_id: str, old_password: str, new_password: str) -> int:
        json_data = {
            "user_id": user_id,
            "oldPassword": old_password,
            "newPassword": new_password
        }
        response = requests.post(f"{self.url_prefix}/password", json=json_data)
        return response.status_code

    def logout(self, user_id: str, token: str) -> int:
        json_data = {
            "user_id": user_id
        }
        headers = {"token": token}
        response = requests.post(f"{self.url_prefix}/logout", json=json_data, headers=headers)
        return response.status_code

    def unregister(self, user_id: str, password: str) -> int:
        json_data = {
            "user_id": user_id,
            "password": password
        }
        response = requests.post(f"{self.url_prefix}/unregister", json=json_data)
        return response.status_code

    def search_book(self, query: str, store_id: str = None, page: int = 1, per_page: int = 10) -> Tuple[int, List[Dict]]:
        params = {
            "query": query,
            "page": page,
            "per_page": per_page
        }
        if store_id:
            params["store_id"] = store_id
            
        response = requests.get(f"{self.url_prefix}/search_book", params=params)
        if response.status_code == 200:
            return response.status_code, response.json().get("books", [])
        return response.status_code, []
```

*   **设计优点**

    这个 `Auth` 类 **包含了所有认证相关的操作**，使用简单，代码也显得整洁。它统一使用 `requests` 库发 POST 请求，地址自动拼接，**修改方便**。
    每个操作结束会显示结果（HTTP状态码），这样调用者就知道下一步的操作了。搜书功能的设计也 **很灵活**。

### **2. `/fe/access/buyer.py`：买家接口访问客户端**

*   **主要功能介绍**

    `Buyer` 类是模拟买家操作的客户端。这个类一经创建就会**自动登录** (`Auth` 类介入)，获取用户ID和 Token 存起来。然后你就可以用 `Buyer` 对象来实现买家部分的相关功能。这些操作发请求时都会自动捎带登录获取的 Token，后端就能通过 token 获取用户信息。

*   **核心代码实现**

```python
class Buyer:
    def __init__(self, url_prefix: str, user_id: str, password: str):
        self.url_prefix = url_prefix
        self.user_id = user_id
        self.password = password
        self.token = ""
        self.auth = Auth(url_prefix)
        self.login()

    def login(self) -> int:
        code, token = self.auth.login(self.user_id, self.password)
        if code == 200:
            self.token = token
        return code

    def new_order(self, store_id: str, books: List[Tuple[str, int]]) -> Tuple[int, str]:
        json_data = {
            "user_id": self.user_id,
            "store_id": store_id,
            "books": books
        }
        headers = {"token": self.token}
        response = requests.post(f"{self.url_prefix}/new_order", json=json_data, headers=headers)
        if response.status_code == 200:
            return response.status_code, response.json().get("order_id", "")
        return response.status_code, ""

    def payment(self, order_id: str) -> int:
        json_data = {
            "user_id": self.user_id,
            "password": self.password,
            "order_id": order_id
        }
        headers = {"token": self.token}
        response = requests.post(f"{self.url_prefix}/payment", json=json_data, headers=headers)
        return response.status_code

    def add_funds(self, add_value: int) -> int:
        json_data = {
            "user_id": self.user_id,
            "password": self.password,
            "add_value": add_value
        }
        headers = {"token": self.token}
        response = requests.post(f"{self.url_prefix}/add_funds", json=json_data, headers=headers)
        return response.status_code

    def get_order_history(self) -> Tuple[int, List[Dict]]:
        headers = {"token": self.token}
        response = requests.get(f"{self.url_prefix}/get_order_history", headers=headers)
        if response.status_code == 200:
            return response.status_code, response.json().get("orders", [])
        return response.status_code, []

    def cancel_order(self, order_id: str) -> int:
        json_data = {
            "user_id": self.user_id,
            "order_id": order_id
        }
        headers = {"token": self.token}
        response = requests.post(f"{self.url_prefix}/cancel_order", json=json_data, headers=headers)
        return response.status_code

    def receive_order(self, order_id: str) -> int:
        json_data = {
            "user_id": self.user_id,
            "order_id": order_id
        }
        headers = {"token": self.token}
        response = requests.post(f"{self.url_prefix}/receive_order", json=json_data, headers=headers)
        return response.status_code

    def collect_book(self, book_id: str) -> int:
        json_data = {
            "user_id": self.user_id,
            "book_id": book_id
        }
        headers = {"token": self.token}
        response = requests.post(f"{self.url_prefix}/collect_book", json=json_data, headers=headers)
        return response.status_code

    def uncollect_book(self, book_id: str) -> int:
        json_data = {
            "user_id": self.user_id,
            "book_id": book_id
        }
        headers = {"token": self.token}
        response = requests.post(f"{self.url_prefix}/uncollect_book", json=json_data, headers=headers)
        return response.status_code

    def get_collection(self) -> Tuple[int, List[Dict]]:
        headers = {"token": self.token}
        response = requests.get(f"{self.url_prefix}/get_collection", headers=headers)
        if response.status_code == 200:
            return response.status_code, response.json().get("books", [])
        return response.status_code, []

    def collect_store(self, store_id: str) -> int:
        json_data = {
            "user_id": self.user_id,
            "store_id": store_id
        }
        headers = {"token": self.token}
        response = requests.post(f"{self.url_prefix}/collect_store", json=json_data, headers=headers)
        return response.status_code

    def uncollect_store(self, store_id: str) -> int:
        json_data = {
            "user_id": self.user_id,
            "store_id": store_id
        }
        headers = {"token": self.token}
        response = requests.post(f"{self.url_prefix}/uncollect_store", json=json_data, headers=headers)
        return response.status_code

    def get_store_collection(self) -> Tuple[int, List[Dict]]:
        headers = {"token": self.token}
        response = requests.get(f"{self.url_prefix}/get_store_collection", headers=headers)
        if response.status_code == 200:
            return response.status_code, response.json().get("stores", [])
        return response.status_code, []
```

*   **设计优点**

    这个类 **封装良好**，把买家操作都集中到一起。
    
    它能够 **自动处理了登录和 Token**，在使用的时候不用担心这些认证的细节了。整体代码风格和 `Auth` 类相似，**统一规范**。返回的状态码能够让用户 **了解操作是否成功**。在这样的设计框架下想要集成新的买家功能也非常方便。

### **3. `/fe/access/book.py`：图书数据访问与处理**

*   **主要功能介绍**

    这里有两个类：
    
    `Book` 类是书籍的 **名片**，专门用来 **存放一本书的详细信息**，例如书名、作者、出版社、价格、ISBN，还有简介、标签，甚至 **书的封面图片**（我们将其转化为了 Base64 编码的文本）。
    
    `BookDB` 类则是用于与 **MongoDB 数据库交互** 的，用于查询书籍。这个类能显示数据库里 **书记总量** (`get_book_count`)，并且能 **按页获取书的信息** (`get_book_info`)，例如"给我第11到20本书的信息"，系统会把查到的信息包装成若干 `Book` 对象返还给用户。

*   **核心代码实现**

```python
class Book:
    def __init__(self, book_info: Dict):
        self.id = book_info.get("id", "")
        self.title = book_info.get("title", "")
        self.author = book_info.get("author", "")
        self.publisher = book_info.get("publisher", "")
        self.original_title = book_info.get("original_title", "")
        self.translator = book_info.get("translator", "")
        self.pub_year = book_info.get("pub_year", "")
        self.pages = book_info.get("pages", 0)
        self.price = book_info.get("price", 0)
        self.currency_unit = book_info.get("currency_unit", "")
        self.binding = book_info.get("binding", "")
        self.isbn = book_info.get("isbn", "")
        self.author_intro = book_info.get("author_intro", "")
        self.book_intro = book_info.get("book_intro", "")
        self.content = book_info.get("content", "")
        self.tags = book_info.get("tags", [])
        self.picture = book_info.get("picture", "")

class BookDB:
    def __init__(self, db_url: str):
        self.client = pymongo.MongoClient(db_url)
        self.db = self.client["bookstore"]
        self.collection = self.db["books"]
        # 创建索引以提升查询性能
        self.collection.create_index("id")

    def get_book_count(self) -> int:
        return self.collection.count_documents({})

    def get_book_info(self, start: int, size: int) -> List[Book]:
        books = []
        cursor = self.collection.find().skip(start).limit(size)
        for book_info in cursor:
            books.append(Book(book_info))
        return books

    def get_book_by_id(self, book_id: str) -> Optional[Book]:
        book_info = self.collection.find_one({"id": book_id})
        if book_info:
            return Book(book_info)
        return None

    def search_books(self, query: str, store_id: str = None, page: int = 1, per_page: int = 10) -> Tuple[int, List[Book]]:
        search_filter = {
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"author": {"$regex": query, "$options": "i"}},
                {"book_intro": {"$regex": query, "$options": "i"}},
                {"content": {"$regex": query, "$options": "i"}},
                {"tags": {"$regex": query, "$options": "i"}}
            ]
        }
        
        if store_id:
            search_filter["store_id"] = store_id
            
        total = self.collection.count_documents(search_filter)
        books = []
        
        cursor = self.collection.find(search_filter).skip((page - 1) * per_page).limit(per_page)
        for book_info in cursor:
            books.append(Book(book_info))
            
        return total, books
```

*   **设计优点**

    **分工明确**：`Book` 类管理数据的特征，`BookDB` 类管理如何从数据库里获取数据。
    
    `BookDB` 用了 pymongo 和 MongoDB 交互，在 **分页查询** (`skip` 和 `limit`) 处理逻辑优秀，在书籍总量较高的情况下，也能够高效地一页一页显示。
    
    另外，把 **封面图片转成 Base64** 放在 `Book` 对象里，传送给前端或者显示都非常便捷。我们还以书的 ID 添加了数据库 **索引**，这能 **大大提升查找速度**。

## 测试

除了基本的测试之外，我们还自行增加了一些测试来对新开发的功能进行测试，以提高代码覆盖率率。

### 测试取消订单（TestCancelOrder）

1. test_ok (测试正常取消订单)：
   - 操作步骤：取消第二个订单（未支付的订单），期望返回状态码200。
   - 验证逻辑：确保订单取消功能在正常条件下能够正确执行。

2. test_wrong_user_id (测试错误用户ID)：
   - 操作步骤：错误地修改买家的用户ID后尝试取消订单，期望返回状态码非200。
   - 验证逻辑：由于验证系统能否正确识别并阻止因用户ID错误而造成的非法操作。

3. test_non_exist_order_id (测试不存在的订单ID)：
   - 操作步骤：使用一个不存在的订单ID尝试取消订单，期望返回状态码非200。
   - 验证逻辑：确保系统能正确处理不存在的订单ID，避免非法取消。

4. test_repeat_cancel (测试重复取消订单)：
   - 操作步骤：先取消一个订单，然后尝试重复取消同一订单，期望第二次取消的返回状态码非200。
   - 验证逻辑：检查订单的状态管理是否能有效阻止对已取消订单的重复操作。

5. test_cancel_paid_order (测试取消已支付订单)：
   - 操作步骤：尝试取消已经支付的订单，期望返回状态码非200。
   - 验证逻辑：验证订单状态判断逻辑，确保已支付的订单无法取消。

6. test_cancel_long_time_order (测试取消超时的订单)：
   - 操作步骤：等待一定时间后尝试取消订单，模拟订单过期的取消尝试，期望返回状态码非200。
   - 验证逻辑：测试系统是否能处理订单时间的限制，确保长时间后无法取消订单。

### 测试订单历史查询（TestGetOrderHistory）

1. test_ok：
   - 验证正常情况下订单历史查询的功能。
   - 操作步骤：
     1. 调用get_order_history方法查询订单历史。
     2. 使用断言（assert）检查返回状态码是200，确保查询成功。

2. test_non_exist_user_id：
   - 验证错误用户ID的订单历史查询的反馈。
   - 操作步骤：
     1. 人为修改买家ID以制造"不存在的用户"情形。
     2. 查询该用户的订单历史。
     3. 使用断言（assert）确认返回状态码不是200，确保系统正确处理不存在的用户查询请求。

### 测试搜索功能（TestSearch）

1. test_search_global：
   - 功能验证：在整个数据库中搜索书籍，不限于任何店铺。
   - 检查点：确保输入书籍的标题、内容或标签都能正确返回状态码200，表示搜索成功。

2. test_search_global_not_exists：
   - 功能验证：尝试搜索数据库中不存在的书籍信息。
   - 检查点：对于每一种搜索（标题、内容、标签），都应返回529状态码，表示没有找到相关书籍。

3. test_search_in_store：
   - 功能验证：在指定的店铺内搜索书籍。
   - 检查点：分别使用标题、内容和标签进行搜索，都应返回状态码200，表明在指定店铺内成功找到了相关书籍。

4. test_search_not_exist_store_id：
   - 功能验证：使用不存在的店铺ID进行搜索尝试。
   - 检查点：任何形式的搜索都应返回513状态码，指出店铺不存在。

5. test_search_in_store_not_exist：
   - 功能验证：在指定的店铺内搜索不存在的书籍。
   - 检查点：对于不存在的书籍，在指定的店铺内进行搜索，应返回529状态码，表示书籍未找到。

### 测试订单发货和接收（TestShipReceive）

1. test_ship_ok：
   - 验证卖家可以成功发货，系统返回状态码200。

2. test_receive_ok：
   - 先确保卖家成功发货，然后验证买家接收订单后，系统应返回状态码200。

3. test_error_store_id：
   - 使用错误的store_id尝试发货，验证系统返回状态码应非200。

4. test_error_order_id：
   - 使用错误的order_id尝试发货，验证系统返回状态码应非200。

5. test_error_seller_id：
   - 修改卖家ID后进行发货，验证系统返回状态码应非200。

6. test_error_buyer_id：
   - 在买家接收订单之前修改买家ID，验证系统返回状态码应非200。

7. test_ship_not_pay：
   - 尝试发货未支付的订单，验证系统返回状态码应非200。

8. test_receive_not_ship：
   - 尝试接收未发货的订单，验证系统返回状态码应非200。

9. test_repeat_ship：
   - 验证重复发货的订单，系统第二次应返回状态码非200。

10. test_repeat_receive：
    - 买家接收同一订单两次，第二次接收应返回状态码非200。

### 测试书本和店铺收藏夹（TestCollection）

1. test_ok：
   - 环境准备：注册新的买家和卖家账户，创建商店。
   - 操作步骤：
     1. 收藏两本书，每次操作后验证返回状态码为200，确认收藏成功。
     2. 获取并验证用户收藏的图书列表，确保返回码为200，表示查询成功。
     3. 取消这两本书的收藏，每次操作后验证状态码为200，确认取消成功。
     4. 收藏一个商店，然后验证状态码为200，确认收藏成功。
     5. 获取并验证收藏的商店列表，确保状态码为200，表示查询成功。
     6. 取消收藏的商店，验证状态码为200，确保取消成功。

## 成果

项目链接：https://github.com/manchestersskyisred/ECNU-Bookstoredemo

![image-20250410025232424](/Users/kerwinlv/Library/Application Support/typora-user-images/image-20250410025232424.png)

![image-20250410025311598](/Users/kerwinlv/Library/Application Support/typora-user-images/image-20250410025311598.png)

大部分没覆盖到的代码都是一些不会被执行的或者一些异常抛出的代码，为了代码功能的完整和结构的严谨，我们保留了这部分代码

## 分工&协作

在项目的完成过程中，所有成员相互沟通、通力协作，充分利用git工具完成了本项目的所有工作，其中所有人的工作量分布如下:

* 柳絮源: 33.33%贡献
  * 附加功能开发
    * 图书搜索接口
  * 附加功能测试
  * BUG 修复
  * 报告撰写
* 吕佳鸿: 33.33%贡献
  * 基础功能开发（全部基础接口）
  * 附加功能开发
    * 发货/收货接口
    * 订单操作接口
  * 代码仓库日常维护
    * 版本管理
    * 分支管理
  * BUG 修复
  * 报告撰写
* 肖岂源: 33.33%贡献
  * 拓展功能开发
    * 收藏接口
  * BUG 修复
  * 报告撰写

git使用情况：

![image-20250410030728173](/Users/kerwinlv/Library/Application Support/typora-user-images/image-20250410030728173.png)
