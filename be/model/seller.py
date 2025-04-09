import time
import logging
import pymongo
from typing import Dict, List, Tuple, Any, Optional, Union
from be.model import error
from be.model import db_conn

logger = logging.getLogger(__name__)

class Seller(db_conn.DBConn):
    def __init__(self):
        super().__init__()
        self.db = self.conn

    def _handle_error(self, error_code: int, error_msg: str, extra_data: Any = None) -> Tuple:
        logger.error(f"Error {error_code}: {error_msg}")
        if extra_data:
            return error_code, error_msg, extra_data
        return error_code, error_msg

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

    def view_orders(self, user_id: str, store_id: str) -> Tuple[int, str, List[Dict]]:
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)

            orders = list(self.db['order_history'].find({'store_id': store_id}))
            if not orders:
                return 404, "No orders found for this store", []

            return 200, "ok", orders
            
        except pymongo.errors.PyMongoError as e:
            return self._handle_error(528, str(e))
        except Exception as e:
            return self._handle_error(530, f"Unexpected error: {str(e)}")

