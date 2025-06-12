import uuid
import json
import logging
import psycopg2
from threading import Timer
from be.model import db_conn
from be.model import error


class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(self, user_id: str, store_id: str, id_and_count: [(str, int)]) -> (int, str, str):
        order_id = ""
        try:
            # 验证用户和商店存在性
            user_exists = self.user_id_exist(user_id)
            store_exists = self.store_id_exist(store_id)
            
            if not user_exists:
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not store_exists:
                return error.error_non_exist_store_id(store_id) + (order_id,)

            # 生成唯一订单ID
            order_id = "{}_{}_{}" .format(user_id, store_id, str(uuid.uuid1()))

            # 开始数据库事务处理
            order_details = []
            with self.conn:
                with self.conn.cursor() as cur:
                    # 处理每个商品项目
                    for book_id, count in id_and_count:
                        # 查询商品库存和信息
                        stock_query = "SELECT stock_level, book_info FROM store WHERE store_id = %s AND book_id = %s;"
                        cur.execute(stock_query, (store_id, book_id))
                        result = cur.fetchone()
                        
                        if result is None:
                            return error.error_non_exist_book_id(book_id) + (order_id,)
                        
                        stock_level, book_info = result
                        book_data = json.loads(book_info)
                        price = book_data.get("price")

                        # 库存检查
                        if count > stock_level:
                            return error.error_stock_level_low(book_id) + (order_id,)

                        # 库存扣减操作
                        update_stock_sql = ("UPDATE store SET stock_level = stock_level - %s "
                                           "WHERE store_id = %s AND book_id = %s AND stock_level >= %s")
                        cur.execute(update_stock_sql, (count, store_id, book_id, count))
                        
                        if cur.rowcount == 0:
                            return error.error_stock_level_low(book_id) + (order_id,)

                        # 构建订单详情数据
                        detail_item = {"book_id": book_id, "count": count, "price": price}
                        order_details.append(detail_item)

                    # 批量插入订单详情
                    detail_insert_sql = ("INSERT INTO new_order_detail(order_id, book_id, count, price) "
                                        "VALUES(%s, %s, %s, %s);")
                    detail_values = [(order_id, detail["book_id"], detail["count"], detail["price"]) 
                                   for detail in order_details]
                    cur.executemany(detail_insert_sql, detail_values)

                    # 插入主订单记录
                    order_insert_sql = "INSERT INTO new_order(order_id, store_id, user_id) VALUES(%s, %s, %s);"
                    cur.execute(order_insert_sql, (order_id, store_id, user_id))

                    # 创建订单历史记录
                    history_insert_sql = ("INSERT INTO order_history(order_id, user_id, store_id, status) "
                                         "VALUES(%s, %s, %s, %s);")
                    cur.execute(history_insert_sql, (order_id, user_id, store_id, "pending"))

                    # 插入历史详情记录
                    history_detail_sql = ("INSERT INTO order_history_detail(order_id, book_id, count, price) "
                                         "VALUES(%s, %s, %s, %s);")
                    history_values = [(order_id, detail["book_id"], detail["count"], detail["price"]) 
                                    for detail in order_details]
                    cur.executemany(history_detail_sql, history_values)

            # 设置订单超时自动取消
            timeout_timer = Timer(10.0, self.cancel_order, args=[user_id, order_id])
            timeout_timer.start()

            return 200, "ok", order_id

        except psycopg2.Error as e:
            error_msg = "{}".format(str(e))
            logging.info("528, {}".format(error_msg))
            return 528, error_msg, ""
        except BaseException as e:
            error_msg = "{}".format(str(e))
            logging.info("530, {}".format(error_msg))
            return 530, error_msg, ""

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            with self.conn:
                with self.conn.cursor() as cur:
                    # 获取订单基本信息
                    order_query = "SELECT user_id, store_id FROM new_order WHERE order_id = %s;"
                    cur.execute(order_query, (order_id,))
                    order_info = cur.fetchone()
                    
                    if order_info is None:
                        return error.error_invalid_order_id(order_id)

                    buyer_id, store_id = order_info

                    # 验证订单所有权
                    if buyer_id != user_id:
                        return error.error_authorization_fail()

                    # 获取买家账户信息
                    buyer_query = 'SELECT balance, password FROM "user" WHERE user_id = %s;'
                    cur.execute(buyer_query, (buyer_id,))
                    buyer_info = cur.fetchone()
                    
                    if buyer_info is None:
                        return error.error_non_exist_user_id(buyer_id)
                    
                    balance, buyer_password = buyer_info

                    # 密码验证
                    if password != buyer_password:
                        return error.error_authorization_fail()

                    # 查找卖家ID
                    seller_query = "SELECT user_id FROM user_store WHERE store_id = %s;"
                    cur.execute(seller_query, (store_id,))
                    seller_info = cur.fetchone()
                    
                    if seller_info is None:
                        return error.error_non_exist_store_id(store_id)
                    
                    seller_id = seller_info[0]

                    # 验证卖家存在
                    if not self.user_id_exist(seller_id):
                        return error.error_non_exist_user_id(seller_id)

                    # 计算订单总金额
                    price_query = "SELECT SUM(count * price) FROM new_order_detail WHERE order_id = %s;"
                    cur.execute(price_query, (order_id,))
                    total_price = cur.fetchone()[0]

                    # 余额检查
                    if balance < total_price:
                        return error.error_not_sufficient_funds(order_id)

                    # 执行资金转移 - 从买家扣款
                    buyer_deduct_sql = ('UPDATE "user" SET balance = balance - %s '
                                       'WHERE user_id = %s AND balance >= %s')
                    cur.execute(buyer_deduct_sql, (total_price, buyer_id, total_price))
                    
                    if cur.rowcount == 0:
                        return error.error_not_sufficient_funds(order_id)

                    # 执行资金转移 - 给卖家加款
                    seller_credit_sql = 'UPDATE "user" SET balance = balance + %s WHERE user_id = %s'
                    cur.execute(seller_credit_sql, (total_price, seller_id))
                    
                    if cur.rowcount == 0:
                        return error.error_non_exist_user_id(buyer_id)

                    # 清理待处理订单记录
                    delete_order_sql = "DELETE FROM new_order WHERE order_id = %s"
                    cur.execute(delete_order_sql, (order_id,))
                    
                    if cur.rowcount == 0:
                        return error.error_invalid_order_id(order_id)

                    delete_detail_sql = "DELETE FROM new_order_detail WHERE order_id = %s"
                    cur.execute(delete_detail_sql, (order_id,))
                    
                    if cur.rowcount == 0:
                        return error.error_invalid_order_id(order_id)

                    # 更新订单状态为已支付
                    update_status_sql = "UPDATE order_history SET status = 'paid' WHERE order_id = %s;"
                    cur.execute(update_status_sql, (order_id,))
                    
                    if cur.rowcount == 0:
                        return error.error_invalid_order_id(order_id)

            return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            with self.conn:
                with self.conn.cursor() as cur:
                    # 验证用户身份
                    auth_query = 'SELECT password FROM "user" WHERE user_id = %s;'
                    cur.execute(auth_query, (user_id,))
                    user_record = cur.fetchone()
                    
                    if user_record is None:
                        return error.error_authorization_fail()
                    
                    stored_password = user_record[0]
                    if password != stored_password:
                        return error.error_authorization_fail()

                    # 执行余额增加
                    balance_update_sql = 'UPDATE "user" SET balance = balance + %s WHERE user_id = %s'
                    cur.execute(balance_update_sql, (add_value, user_id))
                    
                    if cur.rowcount == 0:
                        return error.error_non_exist_user_id(user_id)

            return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

    def get_order_history(self, user_id: str) -> (int, str, [dict]):
        try:
            # 查询用户的订单历史
            history_query = "SELECT order_id FROM order_history WHERE user_id = %s;"
            self.cur.execute(history_query, (user_id,))
            order_records = self.cur.fetchall()

            if not order_records:
                return error.error_non_exist_user_id(user_id) + ([],)

            order_list = []
            for record in order_records:
                order_id = record[0]

                # 获取每个订单的详细信息
                detail_query = ("SELECT book_id, count, price FROM order_history_detail "
                               "WHERE order_id = %s;")
                self.cur.execute(detail_query, (order_id,))
                
                order_detail_list = []
                for detail_record in self.cur.fetchall():
                    book_id, count, price = detail_record
                    order_detail = {
                        "book_id": book_id,
                        "count": count,
                        "price": price
                    }
                    order_detail_list.append(order_detail)

                order_info = {
                    "order_id": order_id,
                    "order_detail": order_detail_list
                }
                order_list.append(order_info)

        except psycopg2.Error as e:
            return 528, "{}".format(str(e)), []
        except BaseException as e:
            return 530, "{}".format(str(e)), []
        finally:
            self.cur.close()
            self.conn.close()

        return 200, "ok", order_list

    def cancel_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            with self.conn:
                with self.conn.cursor() as cur:
                    # 验证订单存在性和权限
                    order_check_sql = ("SELECT user_id, status FROM order_history "
                                      "WHERE order_id = %s;")
                    cur.execute(order_check_sql, (order_id,))
                    order_record = cur.fetchone()
                    
                    if order_record is None:
                        return error.error_invalid_order_id(order_id)
                    
                    db_user_id, status = order_record

                    # 权限验证
                    if db_user_id != user_id:
                        return error.error_authorization_fail()

                    # 状态检查
                    if status != "pending":
                        return error.error_invalid_order_id(order_id)

                    # 获取需要恢复的库存信息
                    detail_query = ("SELECT book_id, count FROM new_order_detail "
                                   "WHERE order_id = %s;")
                    cur.execute(detail_query, (order_id,))
                    order_details = cur.fetchall()

                    # 恢复所有商品库存
                    for book_id, count in order_details:
                        restore_stock_sql = ("UPDATE store SET stock_level = stock_level + %s "
                                           "WHERE book_id = %s")
                        cur.execute(restore_stock_sql, (count, book_id))
                    
                    # 删除待处理订单
                    remove_order_sql = "DELETE FROM new_order WHERE order_id = %s"
                    cur.execute(remove_order_sql, (order_id,))

                    # 标记订单为已取消
                    cancel_status_sql = ("UPDATE order_history SET status = 'cancelled' "
                                        "WHERE order_id = %s;")
                    cur.execute(cancel_status_sql, (order_id,))
                    
            return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

    def receive_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            with self.conn:
                with self.conn.cursor() as cur:
                    # 检查订单状态和权限
                    status_check_sql = "SELECT user_id, status FROM order_history WHERE order_id = %s;"
                    cur.execute(status_check_sql, (order_id,))
                    status_record = cur.fetchone()
                    
                    if not status_record:
                        return error.error_invalid_order_id(order_id)

                    buyer_id, status = status_record

                    # 用户权限验证
                    if buyer_id != user_id:
                        return error.error_authorization_fail()

                    # 发货状态检查，只有shipped状态才能收货
                    if status != "shipped":
                        if status == "received":
                            return error.error_invalid_status(order_id)
                        else:
                            return error.error_not_shipped(order_id)

                    # 更新为已收货状态，确保只有shipped状态的订单能被更新
                    receive_status_sql = "UPDATE order_history SET status = 'received' WHERE order_id = %s AND status = 'shipped';"
                    cur.execute(receive_status_sql, (order_id,))
                    
                    if cur.rowcount == 0:
                        return error.error_invalid_status(order_id)

            return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
    def get_collection(self, user_id):
        try:
            collection_books = []
            with self.conn:
                with self.conn.cursor() as cur:
                    collection_query = "SELECT book_id FROM collections WHERE user_id = %s;"
                    cur.execute(collection_query, (user_id,))
                    book_records = cur.fetchall()
                    
                    for record in book_records:
                        book_id = record[0]
                        collection_books.append(book_id)

            return 200, "ok," + ",".join(collection_books)
            
        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

    def collect_book(self, user_id, book_id):
        try:
            # 用户存在性检查
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
                
            with self.conn:
                with self.conn.cursor() as cur:
                    # 添加到收藏列表
                    collect_insert_sql = "INSERT INTO collections (user_id, book_id) VALUES (%s, %s);"
                    cur.execute(collect_insert_sql, (user_id, book_id))
                    rows_affected = cur.rowcount
                    
                if rows_affected == 0:
                    return 200, "re-collect"
                else:
                    return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

    def uncollect_book(self, user_id, book_id):
        try:
            # 用户存在性检查
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
                
            with self.conn:
                with self.conn.cursor() as cur:
                    # 从收藏列表移除
                    uncollect_delete_sql = "DELETE FROM collections WHERE user_id = %s AND book_id = %s;"
                    cur.execute(uncollect_delete_sql, (user_id, book_id))
                    rows_affected = cur.rowcount
                    
                if rows_affected == 0:
                    return 200, "entry not found or failed to delete"
                else:
                    return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

    def get_user_orders(self, user_id: str, order_status: str = "") -> (int, str, list):
        try:
            # 用户存在性检查
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + ([],)

            orders = []
            with self.conn:
                with self.conn.cursor() as cur:
                    if order_status:
                        # 查询指定状态的订单
                        query = "SELECT order_id, store_id, status FROM order_history WHERE user_id = %s AND status = %s;"
                        cur.execute(query, (user_id, order_status))
                    else:
                        # 查询所有订单
                        query = "SELECT order_id, store_id, status FROM order_history WHERE user_id = %s;"
                        cur.execute(query, (user_id,))
                    
                    order_records = cur.fetchall()
                    
                    for record in order_records:
                        order_id, store_id, status = record
                        order_info = {
                            "order_id": order_id,
                            "store_id": store_id,
                            "status": status
                        }
                        orders.append(order_info)

            return 200, "ok", orders

        except psycopg2.Error as e:
            return 528, "{}".format(str(e)), []
        except BaseException as e:
            return 530, "{}".format(str(e)), []