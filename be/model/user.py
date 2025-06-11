import jwt
import time
import logging
import sqlite3 as sqlite
from typing import Tuple, Optional
from be.model import error, db_conn
import psycopg2


class User(db_conn.DBConn):
    token_lifetime: int = 3600  # 3600 seconds

    def __init__(self):
        super().__init__()

    def __check_token(self, user_id: str, db_token: str, token: str) -> bool:
        if db_token != token:
            return False
        try:
            jwt_text = self.jwt_decode(encoded_token=token, user_id=user_id)
            ts = jwt_text.get("timestamp")
            if ts and 0 <= time.time() - ts < self.token_lifetime:
                return True
        except jwt.exceptions.InvalidSignatureError as e:
            logging.error(str(e))
        return False

    def register(self, user_id: str, password: str) -> Tuple[int, str]:
        if self.user_id_exist(user_id):
            return error.error_exist_user_id(user_id)
        try:
            terminal = f"terminal_{time.time()}"
            with self.conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO "user"(user_id, password, balance, token, terminal) '
                    'VALUES (%s, %s, %s, %s, %s)',
                    (user_id, password, 0, self.jwt_encode(user_id, terminal), terminal),
                )
            self.conn.commit()
            return 200, "ok"
        except psycopg2.Error as e:
            return 528, str(e)

    def check_token(self, user_id: str, token: str) -> Tuple[int, str]:
        with self.conn.cursor() as cur:
            cur.execute('SELECT token FROM "user" WHERE user_id=%s', (user_id,))
            row = cur.fetchone()
            if not row or not self.__check_token(user_id, row[0], token):
                return error.error_authorization_fail()
        return 200, "ok"

    def check_password(self, user_id: str, password: str) -> Tuple[int, str]:
        with self.conn.cursor() as cur:
            cur.execute('SELECT password FROM "user" WHERE user_id=%s', (user_id,))
            row = cur.fetchone()
            if not row or password != row[0]:
                return error.error_authorization_fail()
        return 200, "ok"

    def login(self, user_id: str, password: str, terminal: str) -> Tuple[int, str, Optional[str]]:
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, None

            token = self.jwt_encode(user_id, terminal)
            with self.conn.cursor() as cur:
                cur.execute(
                    'UPDATE "user" SET token=%s, terminal=%s WHERE user_id=%s RETURNING token;',
                    (token, terminal, user_id),
                )
            self.conn.commit()
            return 200, "ok", token
        except psycopg2.Error as e:
            return 528, str(e), None
        except Exception as e:
            return 530, str(e), None

    def logout(self, user_id: str, token: str) -> Tuple[int, str]:
        try:
            code, message = self.check_token(user_id, token)
            if code != 200:
                return code, message

            terminal = f"terminal_{time.time()}"
            dummy_token = self.jwt_encode(user_id, terminal)
            with self.conn.cursor() as cur:
                cur.execute(
                    'UPDATE "user" SET token=%s, terminal=%s WHERE user_id=%s RETURNING token;',
                    (dummy_token, terminal, user_id),
                )
                if cur.rowcount == 0:
                    return error.error_authorization_fail()
            self.conn.commit()
            return 200, "ok"
        except psycopg2.Error as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)

    def unregister(self, user_id: str, password: str) -> Tuple[int, str]:
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message

            with self.conn.cursor() as cur:
                cur.execute('DELETE FROM "user" WHERE user_id=%s', (user_id,))
                if cur.rowcount != 1:
                    return error.error_authorization_fail()
            self.conn.commit()
            return 200, "ok"
        except psycopg2.Error as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)

    def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> Tuple[int, str]:
        try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message

            terminal = f"terminal_{time.time()}"
            token = self.jwt_encode(user_id, terminal)
            with self.conn.cursor() as cur:
                cur.execute(
                    'UPDATE "user" SET password=%s, token=%s, terminal=%s WHERE user_id=%s RETURNING token;',
                    (new_password, token, terminal, user_id),
                )
                if cur.rowcount == 0:
                    return error.error_authorization_fail()
            self.conn.commit()
            return 200, "ok"
        except psycopg2.Error as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)

    def search_book(
        self, title: str = '', content: str = '', tag: str = '', store_id: str = ''
    ) -> Tuple[int, str]:
        try:
            book_db = "/Users/kerwinlv/bookstore/data/book.db"
            query_conditions = []
            query_parameters = []

            if title:
                query_conditions.append("title LIKE ?")
                query_parameters.append(f"%{title}%")

            if content:
                query_conditions.append("content LIKE ?")
                query_parameters.append(f"%{content}%")

            if tag:
                query_conditions.append("tags LIKE ?")
                query_parameters.append(f"%{tag}%")

            if store_id:
                with self.conn.cursor() as cur:
                    cur.execute("SELECT book_id FROM store WHERE store_id = %s", (store_id,))
                    book_ids = [row[0] for row in cur.fetchall()]
                if not book_ids:
                    return error.error_non_exist_store_id(store_id)
                placeholders = ",".join("?" for _ in book_ids)
                query_conditions.append(f"id IN ({placeholders})")
                query_parameters.extend(book_ids)

            if not query_conditions:
                return 200, "ok"

            query_string = "SELECT * FROM book WHERE " + " AND ".join(query_conditions)
            with sqlite.connect(book_db) as conn:
                cursor = conn.execute(query_string, query_parameters)
                results = cursor.fetchall()

            if not results:
                return 529, "No matching books found."
            return 200, "ok"
        except (psycopg2.Error, sqlite.Error) as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)

    def jwt_encode(self, user_id: str, terminal: str) -> Optional[str]:
        try:
            payload = {"user_id": user_id, "terminal": terminal, "timestamp": time.time()}
            encoded_token = jwt.encode(payload, key=user_id, algorithm="HS256")
            return encoded_token
        except Exception:
            return None

    def jwt_decode(self, encoded_token: str, user_id: str) -> Optional[dict]:
        try:
            decoded = jwt.decode(encoded_token, key=user_id, algorithms=["HS256"])
            return decoded
        except Exception:
            return None