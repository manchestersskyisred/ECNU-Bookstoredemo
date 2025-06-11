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
            # 检查user, store是否存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)

            # 生成order ID
            order_id = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))

            # 事务开始
            with self.conn:
                with self.conn.cursor() as cur:
                    order_details = []

                    for book_id, count in id_and_count:
                        # 获取book信息
                        cur.execute(
                            "SELECT stock_level, book_info FROM store "
                            "WHERE store_id = %s AND book_id = %s;",
                            (store_id, book_id),
                        )
                        row = cur.fetchone()
                        if row is None:
                            return error.error_non_exist_book_id(book_id) + (order_id,)
                        
                        stock_level, book_info = row
                        book_info_json = json.loads(book_info)
                        price = book_info_json.get("price")

                        # 检查stock level
                        if stock_level < count:
                            return error.error_stock_level_low(book_id) + (order_id,)

                        # 更新 stock level
                        cur.execute(
                            "UPDATE store SET stock_level = stock_level - %s "
                            "WHERE store_id = %s AND book_id = %s AND stock_level >= %s",
                            (count, store_id, book_id, count),
                        )
                        if cur.rowcount == 0:
                            return error.error_stock_level_low(book_id) + (order_id,)

                        # 添加 order details
                        order_details.append({"book_id": book_id, "count": count, "price": price})

                    # 插入到new_order_detail中
                    cur.executemany(
                        "INSERT INTO new_order_detail(order_id, book_id, count, price) "
                        "VALUES(%s, %s, %s, %s);",
                        [(order_id, detail["book_id"], detail["count"], detail["price"]) for detail in order_details],
                    )

                    # 插入到new_order中
                    cur.execute(
                        "INSERT INTO new_order(order_id, store_id, user_id) "
                        "VALUES(%s, %s, %s);",
                        (order_id, store_id, user_id),
                    )

                    # 插入到order_history中
                    cur.execute(
                        "INSERT INTO order_history(order_id, user_id, store_id, status) "
                        "VALUES(%s, %s, %s, %s);",
                        (order_id, user_id, store_id, "pending"),
                    )

                    # 插入到order_history_detail中
                    cur.executemany(
                        "INSERT INTO order_history_detail(order_id, book_id, count, price) "
                        "VALUES(%s, %s, %s, %s);",
                        [(order_id, detail["book_id"], detail["count"], detail["price"]) for detail in order_details],
                    )

            # 超时取消的计时器
            timer = Timer(10.0, self.cancel_order, args=[user_id, order_id])
            timer.start()

            return 200, "ok", order_id

        except psycopg2.Error as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            # 事务开始
            with self.conn:
                with self.conn.cursor() as cur:
                    # 订单信息
                    cur.execute(
                        "SELECT user_id, store_id FROM new_order WHERE order_id = %s;",
                        (order_id,)
                    )
                    order_row = cur.fetchone()
                    if order_row is None:
                        return error.error_invalid_order_id(order_id)

                    buyer_id, store_id = order_row

                    # 权限
                    if buyer_id != user_id:
                        return error.error_authorization_fail()

                    # 买家信息
                    cur.execute(
                        'SELECT balance, password FROM "user" WHERE user_id = %s;',
                        (buyer_id,)
                    )
                    buyer_row = cur.fetchone()
                    if buyer_row is None:
                        return error.error_non_exist_user_id(buyer_id)
                    balance, buyer_password = buyer_row

                    # 验证密码
                    if password != buyer_password:
                        return error.error_authorization_fail()

                    # 卖家信息
                    cur.execute(
                        "SELECT user_id FROM user_store WHERE store_id = %s;",
                        (store_id,)
                    )
                    seller_row = cur.fetchone()
                    if seller_row is None:
                        return error.error_non_exist_store_id(store_id)
                    seller_id = seller_row[0]

                    if not self.user_id_exist(seller_id):
                        return error.error_non_exist_user_id(seller_id)

                    # 总价
                    cur.execute(
                        "SELECT SUM(count * price) FROM new_order_detail WHERE order_id = %s;",
                        (order_id,)
                    )
                    total_price = cur.fetchone()[0]

                    # 买家余额
                    if balance < total_price:
                        return error.error_not_sufficient_funds(order_id)

                    #  执行交易：从买家余额中扣除，加到卖家余额中 
                    cur.execute(
                        'UPDATE "user" SET balance = balance - %s '
                        'WHERE user_id = %s AND balance >= %s',
                        (total_price, buyer_id, total_price),
                    )
                    if cur.rowcount == 0:
                        return error.error_not_sufficient_funds(order_id)

                    cur.execute(
                        'UPDATE "user" SET balance = balance + %s '
                        'WHERE user_id = %s',
                        (total_price, seller_id),
                    )
                    if cur.rowcount == 0:
                        return error.error_non_exist_user_id(buyer_id)

                    # 删除订单及订单详情
                    cur.execute(
                        "DELETE FROM new_order WHERE order_id = %s",
                        (order_id,)
                    )
                    if cur.rowcount == 0:
                        return error.error_invalid_order_id(order_id)

                    cur.execute(
                        "DELETE FROM new_order_detail WHERE order_id = %s",
                        (order_id,)
                    )
                    if cur.rowcount == 0:
                        return error.error_invalid_order_id(order_id)

                    # 更新订单历史状态为 "已支付"
                    cur.execute(
                        "UPDATE order_history SET status = 'paid' WHERE order_id = %s;",
                        (order_id,)
                    )
                    if cur.rowcount == 0:
                        return error.error_invalid_order_id(order_id)

            return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))

        except BaseException as e:
            return 530, "{}".format(str(e))

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            # 开始事务
            with self.conn:
                with self.conn.cursor() as cur:
                    # 获取用户密码
                    cur.execute(
                        'SELECT password FROM "user" WHERE user_id = %s', (user_id,)
                    )
                    row = cur.fetchone()
                    if row is None:
                        return error.error_authorization_fail()

                    # 密码错误
                    if row[0] != password:
                        return error.error_authorization_fail()

                    # 更新余额
                    cur.execute(
                        'UPDATE "user" SET balance = balance + %s WHERE user_id = %s',
                        (add_value, user_id),
                    )
                    if cur.rowcount == 0:
                        return error.error_non_exist_user_id(user_id)

            return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

    def get_order_history(self, user_id: str) -> (int, str, [dict]):
        try:
            # 获取用户的历史订单
            self.cur.execute(
                "SELECT order_id FROM order_history WHERE user_id = %s;",
                (user_id,)
            )
            rows = self.cur.fetchall()

            if not rows:
                return error.error_non_exist_user_id(user_id) + ([],)

            order_list = []
            for row in rows:
                order_id = row[0]

                # 获取订单详情
                self.cur.execute(
                    "SELECT book_id, count, price FROM order_history_detail WHERE order_id = %s;",
                    (order_id,)
                )
                order_detail_list = []
                for detail_row in self.cur.fetchall():
                    book_id, count, price = detail_row
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
            # 事务开始
            with self.conn:
                with self.conn.cursor() as cur:
                    # 检查订单是否存在
                    cur.execute(
                        "SELECT user_id, status FROM order_history "
                        "WHERE order_id = %s;",
                        (order_id,)
                    )
                    order_row = cur.fetchone()
                    if order_row is None:
                        return error.error_invalid_order_id(order_id)
                    
                    db_user_id, status = order_row

                    # 检查用户权限
                    if db_user_id != user_id:
                        return error.error_authorization_fail()

                    # 检查订单状态
                    if status != "pending":
                        return error.error_invalid_order_id(order_id)

                    # 获取订单详情
                    cur.execute(
                        "SELECT book_id, count FROM new_order_detail "
                        "WHERE order_id = %s;",
                        (order_id,)
                    )
                    order_details = cur.fetchall()

                    # 恢复库存
                    for book_id, count in order_details:
                        cur.execute(
                            "UPDATE store SET stock_level = stock_level + %s "
                            "WHERE book_id = %s",
                            (count, book_id),
                        )
                    
                    # 删除订单
                    cur.execute(
                        "DELETE FROM new_order WHERE order_id = %s",
                        (order_id,)
                    )

                    # 更新订单历史状态为 "已取消"
                    cur.execute(
                        "UPDATE order_history SET status = 'cancelled' "
                        "WHERE order_id = %s;",
                        (order_id,)
                    )
            return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
    

    def receive_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            # 事务开始
            with self.conn:
                with self.conn.cursor() as cur:
                    # 检查order是否存在
                    cur.execute(
                        "SELECT user_id, status FROM order_history WHERE order_id = %s;",
                        (order_id,)
                    )
                    row = cur.fetchone()
                    if not row:
                        return error.error_invalid_order_id(order_id)

                    buyer_id, status = row

                    # 检查用户权限
                    if buyer_id != user_id:
                        return error.error_authorization_fail()

                    # 订单状态是否为 shipped
                    if status != "shipped":
                        return error.error_not_shipped(order_id)

                    # 更改订单状态为received
                    cur.execute(
                        "UPDATE order_history SET status = 'received' WHERE order_id = %s;",
                        (order_id,)
                    )
                    if cur.rowcount == 0:
                        return error.error_invalid_order_id(order_id)

            return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        

    def get_collection(self, user_id):
        try:
            ret = []
            # 事务开始
            with self.conn:
                with self.conn.cursor() as cur:
                    cur.execute(
                        "SELECT book_id FROM collections WHERE user_id = %s;",
                        (user_id,)
                    )
                    rows = cur.fetchall()
                    
                    for row in rows:
                        book_id = row[0]
                        ret.append(book_id)

            return 200, "ok," + ",".join(ret)
        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))


    def collect_book(self, user_id, book_id):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            # 事务开始
            with self.conn:
                with self.conn.cursor() as cur:
                    # 检查order是否存在
                    cur.execute(
                        "INSERT INTO collections (user_id, book_id) VALUES (%s, %s);",
                        (user_id, book_id)
                    )
                    added = cur.rowcount
                    
                if added == 0:
                    return 200, "re-collect"
                else:
                    return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))



    def uncollect_book(self, user_id, book_id):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            # 事务开始
            with self.conn:
                with self.conn.cursor() as cur:
                    # 检查order是否存在
                    cur.execute(
                        "DELETE FROM collections WHERE user_id = %s AND book_id = %s;",
                        (user_id, book_id)
                    )
                    added = cur.rowcount
                    
                if added == 0:
                    return 200, "entry not found or failed to delete"
                else:
                    return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
