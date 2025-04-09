import jwt
import time
import logging
import pymongo
from typing import Dict, List, Tuple, Any, Optional, Union
from be.model import error
from be.model import db_conn

logger = logging.getLogger(__name__)

def generate_token(user_id: str, terminal: str) -> str:
    payload = {
        "user_id": user_id, 
        "terminal": terminal, 
        "timestamp": time.time()
    }
    encoded = jwt.encode(
        payload,
        key=user_id,
        algorithm="HS256",
    )
    return encoded.encode("utf-8").decode("utf-8")


def verify_token(token_data: str, user_id: str) -> Dict:
    decoded = jwt.decode(token_data, key=user_id, algorithms="HS256")
    return decoded


class User(db_conn.DBConn):
    token_lifetime: int = 3600

    def __init__(self):
        super().__init__()
        self.db = self.conn

    def _handle_error(self, error_code: int, error_msg: str, extra_data: Any = None) -> Tuple:
        logger.error(f"Error {error_code}: {error_msg}")
        if extra_data:
            return error_code, error_msg, extra_data
        return error_code, error_msg

    def _validate_token(self, user_id: str, stored_token: str, provided_token: str) -> bool:
        try:
            if stored_token != provided_token:
                return False

            token_data = verify_token(provided_token, user_id)
            timestamp = token_data.get("timestamp")
            if timestamp is None:
                return False
            
            current_time = time.time()
            return (current_time - timestamp) <= self.token_lifetime
            
        except jwt.exceptions.InvalidSignatureError as e:
            logger.error(f"Token validation error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected token error: {str(e)}")
            return False

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

    def check_token(self, user_id: str, token: str) -> Tuple[int, str]:
        try:
            db = self.db
            account = db['user'].find_one({'user_id': user_id})
            
            if account is None:
                return error.error_authorization_fail()

            stored_token = account.get('token', '')
            if not self._validate_token(user_id, stored_token, token):
                return error.error_authorization_fail()

            return 200, "ok"
        except pymongo.errors.PyMongoError as e:
            return self._handle_error(528, str(e))
        except Exception as e:
            return self._handle_error(530, f"Unexpected error: {str(e)}")

    def check_password(self, user_id: str, password: str) -> Tuple[int, str]:
        try:
            db = self.db
            query_result = db['user'].find_one(
                {'user_id': user_id}, 
                {'_id': 0, 'password': 1}
            )
            
            if query_result is None:
                return error.error_authorization_fail()

            stored_password = query_result.get('password')
            if stored_password != password:
                return error.error_authorization_fail()

            return 200, "ok"
        except pymongo.errors.PyMongoError as e:
            return self._handle_error(528, str(e))
        except Exception as e:
            return self._handle_error(530, f"Unexpected error: {str(e)}")

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

    def logout(self, user_id: str, token: str) -> Tuple[int, str]:
        try:
            status_code, result_msg = self.check_token(user_id, token)
            if status_code != 200:
                return status_code, result_msg

            device_id = f"terminal_{str(time.time())}"
            temp_token = generate_token(user_id, device_id)

            update_data = {
                'token': temp_token, 
                'terminal': device_id,
                'logout_time': int(time.time())
            }
            
            update_result = self.db['user'].update_one(
                {'user_id': user_id},
                {'$set': update_data}
            )
            
            if not update_result.matched_count:
                return error.error_authorization_fail()
                
            return 200, "ok"
        except pymongo.errors.PyMongoError as e:
            return self._handle_error(528, str(e))
        except Exception as e:
            return self._handle_error(530, f"Unexpected error: {str(e)}")

    def unregister(self, user_id: str, password: str) -> Tuple[int, str]:
        try:
            status_code, result_msg = self.check_password(user_id, password)
            if status_code != 200:
                return status_code, result_msg

            delete_result = self.db['user'].delete_one({'user_id': user_id})
            if delete_result.deleted_count != 1:
                return error.error_authorization_fail()
                
            return 200, "ok"
        except pymongo.errors.PyMongoError as e:
            return self._handle_error(528, str(e))
        except Exception as e:
            return self._handle_error(530, f"Unexpected error: {str(e)}")

    def change_password(self, user_id: str, old_password: str, new_password: str) -> Tuple[int, str]:
        try:
            status_code, result_msg = self.check_password(user_id, old_password)
            if status_code != 200:
                return status_code, result_msg

            device_id = f"terminal_{str(time.time())}"
            auth_token = generate_token(user_id, device_id)
            
            update_data = {
                'password': new_password,
                'token': auth_token,
                'terminal': device_id,
                'password_updated_at': int(time.time())
            }
            
            update_result = self.db['user'].update_one(
                {'user_id': user_id},
                {'$set': update_data}
            )
            
            if not update_result.matched_count:
                return error.error_authorization_fail()
                
            return 200, "ok"
        except pymongo.errors.PyMongoError as e:
            return self._handle_error(528, str(e))
        except Exception as e:
            return self._handle_error(530, f"Unexpected error: {str(e)}")

    def search_book(self, title: str = '', content: str = '', tag: str = '', store_id: str = '') -> Tuple[int, Union[str, List[Dict]]]:
        try:
            db = self.db
            search_criteria = {}

            if title:
                search_criteria['title'] = {"$regex": title}
                
            if content:
                search_criteria['content'] = {"$regex": content}
                
            if tag:
                search_criteria['tags'] = {"$regex": tag}

            if store_id:
                store_query = {"store_id": store_id}
                store_items = list(db["store"].find(store_query))
                
                if not store_items:
                    return error.error_non_exist_store_id(store_id)
                    
                book_ids = [item["book_id"] for item in store_items]
                search_criteria['id'] = {"$in": book_ids}

            search_results = list(db["books"].find(search_criteria))
            
            if not search_results:
                return 529, "No matching books found"
                
            processed_results = []
            for book in search_results:
                book_data = {
                    "id": book.get("id"),
                    "title": book.get("title"),
                    "author": book.get("author"),
                    "price": book.get("price"),
                    "tags": book.get("tags", [])
                }
                processed_results.append(book_data)
                
            return 200, processed_results
            
        except pymongo.errors.PyMongoError as e:
            return self._handle_error(528, str(e))
        except Exception as e:
            return self._handle_error(530, f"Unexpected error: {str(e)}")
