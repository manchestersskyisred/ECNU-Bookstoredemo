import psycopg2
from be.model import error, db_conn


class Seller(db_conn.DBConn):
    def __init__(self):
        super().__init__()

    def _check_exists(self, user_id: str, store_id: str = None, book_id: str = None):
        if not self.user_id_exist(user_id):
            return error.error_non_exist_user_id(user_id)
        if store_id and not self.store_id_exist(store_id):
            return error.error_non_exist_store_id(store_id)
        if book_id and not self.book_id_exist(store_id, book_id):
            return error.error_non_exist_book_id(book_id)
        return None

    def add_book(
        self,
        user_id: str,
        store_id: str,
        book_id: str,
        book_json_str: str,
        stock_level: int,
    ):
        try:
            check = self._check_exists(user_id, store_id)
            if check:
                return check
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            with self.conn:
                with self.conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO store(store_id, book_id, book_info, stock_level) "
                        "VALUES (%s, %s, %s, %s)",
                        (store_id, book_id, book_json_str, stock_level),
                    )

            return 200, "ok"

        except psycopg2.Error as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)

    def add_stock_level(
        self, user_id: str, store_id: str, book_id: str, add_stock_level: int
    ):
        try:
            check = self._check_exists(user_id, store_id, book_id)
            if check:
                return check

            with self.conn:
                with self.conn.cursor() as cur:
                    cur.execute(
                        "UPDATE store SET stock_level = stock_level + %s "
                        "WHERE store_id = %s AND book_id = %s",
                        (add_stock_level, store_id, book_id),
                    )

            return 200, "ok"

        except psycopg2.Error as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            check = self._check_exists(user_id)
            if check:
                return check
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)

            with self.conn:
                with self.conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO user_store(store_id, user_id) VALUES (%s, %s)",
                        (store_id, user_id),
                    )

            return 200, "ok"

        except psycopg2.Error as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)

    def ship_order(self, user_id: str, store_id: str, order_id: str) -> (int, str):
        try:
            check = self._check_exists(user_id, store_id)
            if check:
                return check

            with self.conn:
                with self.conn.cursor() as cur:
                    cur.execute(
                        "SELECT status FROM order_history WHERE order_id = %s;",
                        (order_id,)
                    )
                    row = cur.fetchone()
                    if not row:
                        return error.error_invalid_order_id(order_id)

                    status = row[0]
                    if status != 'paid':
                        return error.error_not_paid(order_id)

                    cur.execute(
                        "UPDATE order_history SET status = 'shipped' WHERE order_id = %s;",
                        (order_id,)
                    )
                    if cur.rowcount == 0:
                        return error.error_invalid_order_id(order_id)

            return 200, "ok"

        except psycopg2.Error as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)