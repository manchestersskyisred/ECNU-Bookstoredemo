import psycopg2
import json
import logging
from typing import Tuple, Optional, Dict, Any
from be.model import error, db_conn


class Seller(db_conn.DBConn):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def _execute_with_error_handling(self, operation_name: str, func) -> Tuple[int, str]:
        """统一的异常处理装饰器"""
        try:
            return func()
        except psycopg2.Error as e:
            self.logger.error(f"{operation_name} failed with database error: {e}")
            return 528, f"Database error: {str(e)}"
        except Exception as e:
            self.logger.error(f"{operation_name} failed with unexpected error: {e}")
            return 530, f"Unexpected error: {str(e)}"

    def _validate_prerequisites(self, user_id: str, store_id: str = None, 
                              book_id: str = None, check_ownership: bool = True) -> Optional[Tuple[int, str]]:
        """统一的前置条件验证"""
        # 检查用户是否存在
        if not self.user_id_exist(user_id):
            return error.error_non_exist_user_id(user_id)
        
        # 检查店铺是否存在
        if store_id:
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            
            # 检查用户是否拥有该店铺
            if check_ownership and not self._check_store_ownership(user_id, store_id):
                return error.error_authorization_fail()
        
        # 检查书籍是否在该店铺中存在
        if book_id and store_id and not self.book_id_exist(store_id, book_id):
            return error.error_non_exist_book_id(book_id)
        
        return None

    def _check_store_ownership(self, user_id: str, store_id: str) -> bool:
        """检查用户是否拥有指定店铺"""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM user_store WHERE user_id = %s AND store_id = %s",
                    (user_id, store_id)
                )
                return cur.fetchone() is not None
        except psycopg2.Error:
            return False

    def _parse_book_info(self, book_json_str: str) -> Dict[str, Any]:
        """解析书籍信息JSON字符串"""
        try:
            return json.loads(book_json_str)
        except json.JSONDecodeError:
            return {}

    def _update_book_catalog(self, book_id: str, book_info: Dict[str, Any], cur):
        """更新书籍目录表"""
        try:
            cur.execute("""
                INSERT INTO book_catalog (book_id, title, author, publisher, price) 
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (book_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    author = EXCLUDED.author,
                    publisher = EXCLUDED.publisher,
                    price = EXCLUDED.price
            """, (
                book_id,
                book_info.get('title', f'Book {book_id}'),
                book_info.get('author', 'Unknown'),
                book_info.get('publisher', 'Unknown'),
                float(book_info.get('price', 0)) if book_info.get('price') else None
            ))
        except (ValueError, psycopg2.Error) as e:
            self.logger.warning(f"Failed to update book catalog for {book_id}: {e}")

    def add_book(self, user_id: str, store_id: str, book_id: str, 
                 book_json_str: str, stock_level: int) -> Tuple[int, str]:
        """添加书籍到店铺"""
        def _add_book_operation():
            # 验证前置条件
            validation_error = self._validate_prerequisites(user_id, store_id)
            if validation_error:
                return validation_error
            
            # 检查书籍是否已存在
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)
            
            # 解析书籍信息
            book_info = self._parse_book_info(book_json_str)
            
            with self.conn:
                with self.conn.cursor() as cur:
                    # 更新书籍目录
                    self._update_book_catalog(book_id, book_info, cur)
                    
                    # 添加到原始store表（保持兼容性）
                    cur.execute(
                        "INSERT INTO store(store_id, book_id, book_info, stock_level) "
                        "VALUES (%s, %s, %s, %s)",
                        (store_id, book_id, book_json_str, stock_level)
                    )
                    
                    # 添加到新的库存表
                    try:
                        cur.execute("""
                            INSERT INTO store_inventory (store_id, book_id, stock_level)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (store_id, book_id) DO UPDATE SET
                                stock_level = EXCLUDED.stock_level
                        """, (store_id, book_id, stock_level))
                    except psycopg2.Error:
                        # 如果新表不存在，忽略错误
                        pass
            
            return 200, "ok"
        
        return self._execute_with_error_handling("add_book", _add_book_operation)

    def add_stock_level(self, user_id: str, store_id: str, book_id: str, 
                       add_stock_level: int) -> Tuple[int, str]:
        """增加库存数量"""
        def _add_stock_operation():
            # 验证前置条件
            validation_error = self._validate_prerequisites(user_id, store_id, book_id)
            if validation_error:
                return validation_error
            
            if add_stock_level <= 0:
                return 400, "Stock level addition must be positive"
            
            with self.conn:
                with self.conn.cursor() as cur:
                    # 更新原始store表
                    cur.execute(
                        "UPDATE store SET stock_level = stock_level + %s "
                        "WHERE store_id = %s AND book_id = %s",
                        (add_stock_level, store_id, book_id)
                    )
                    
                    # 更新新的库存表
                    try:
                        cur.execute("""
                            UPDATE store_inventory 
                            SET stock_level = stock_level + %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE store_id = %s AND book_id = %s
                        """, (add_stock_level, store_id, book_id))
                        
                        # 记录库存变更日志
                        cur.execute("""
                            INSERT INTO inventory_logs (store_id, book_id, change_type, quantity, notes)
                            VALUES (%s, %s, 'restock', %s, 'Manual stock addition')
                        """, (store_id, book_id, add_stock_level))
                    except psycopg2.Error:
                        # 如果新表不存在，忽略错误
                        pass
            
            return 200, "ok"
        
        return self._execute_with_error_handling("add_stock_level", _add_stock_operation)

    def create_store(self, user_id: str, store_id: str) -> Tuple[int, str]:
        """创建新店铺"""
        def _create_store_operation():
            # 验证前置条件
            validation_error = self._validate_prerequisites(user_id)
            if validation_error:
                return validation_error
            
            # 检查店铺是否已存在
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)
            
            with self.conn:
                with self.conn.cursor() as cur:
                    # 在user_store表中添加记录
                    cur.execute(
                        "INSERT INTO user_store(store_id, user_id) VALUES (%s, %s)",
                        (store_id, user_id)
                    )
                    
                    # 在新的store_info表中添加记录
                    try:
                        cur.execute("""
                            INSERT INTO store_info (store_id, store_name, owner_id)
                            VALUES (%s, %s, %s)
                        """, (store_id, f"Store {store_id}", user_id))
                    except psycopg2.Error:
                        # 如果新表不存在，忽略错误
                        pass
            
            return 200, "ok"
        
        return self._execute_with_error_handling("create_store", _create_store_operation)

    def ship_order(self, user_id: str, store_id: str, order_id: str) -> Tuple[int, str]:
        """发货订单"""
        conn = None
        try:
            # 获取新的数据库连接
            from be.model import database
            conn = database.get_db_conn()
            
            # 验证用户存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            
            # 验证用户是否拥有该店铺
            if not self._check_store_ownership(user_id, store_id):
                return error.error_authorization_fail()
            
            with conn:
                with conn.cursor() as cur:
                    # 检查订单状态
                    cur.execute(
                        "SELECT status, store_id FROM order_history WHERE order_id = %s",
                        (order_id,)
                    )
                    row = cur.fetchone()
                    if not row:
                        return error.error_invalid_order_id(order_id)
                    
                    order_status, order_store_id = row
                    
                    # 验证订单属于该店铺
                    if order_store_id != store_id:
                        return error.error_authorization_fail()
                    
                    # 检查并更新订单状态 - 使用原子操作
                    cur.execute(
                        "UPDATE order_history SET status = 'shipped' WHERE order_id = %s AND status = 'paid'",
                        (order_id,)
                    )
                    
                    if cur.rowcount == 0:
                        # 更新失败，检查原因
                        if order_status == 'shipped':
                            return error.error_shipped(order_id)
                        elif order_status != 'paid':
                            return error.error_not_paid(order_id)
                        else:
                            return error.error_invalid_order_id(order_id)
            
            return 200, "ok"
        
        except psycopg2.Error as e:
            self.logger.error(f"ship_order failed with database error: {e}")
            return 528, f"Database error: {str(e)}"
        except Exception as e:
            self.logger.error(f"ship_order failed with unexpected error: {e}")
            return 530, f"Unexpected error: {str(e)}"
        finally:
            if conn:
                conn.close()

    def get_store_books(self, user_id: str, store_id: str) -> Tuple[int, str, list]:
        """获取店铺所有书籍列表"""
        def _get_store_books_operation():
            # 验证前置条件
            validation_error = self._validate_prerequisites(user_id, store_id)
            if validation_error:
                return validation_error[0], validation_error[1], []
            
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT book_id, book_info, stock_level 
                    FROM store 
                    WHERE store_id = %s
                    ORDER BY book_id
                """, (store_id,))
                
                books = []
                for row in cur.fetchall():
                    book_id, book_info, stock_level = row
                    book_data = self._parse_book_info(book_info)
                    books.append({
                        'book_id': book_id,
                        'stock_level': stock_level,
                        'book_info': book_data
                    })
                
                return 200, "ok", books
        
        try:
            return _get_store_books_operation()
        except Exception as e:
            self.logger.error(f"get_store_books failed: {e}")
            return 530, str(e), []

    def update_book_price(self, user_id: str, store_id: str, book_id: str, 
                         new_price: float) -> Tuple[int, str]:
        """更新书籍价格"""
        def _update_price_operation():
            # 验证前置条件
            validation_error = self._validate_prerequisites(user_id, store_id, book_id)
            if validation_error:
                return validation_error
            
            if new_price < 0:
                return 400, "Price cannot be negative"
            
            with self.conn:
                with self.conn.cursor() as cur:
                    # 获取当前书籍信息
                    cur.execute(
                        "SELECT book_info FROM store WHERE store_id = %s AND book_id = %s",
                        (store_id, book_id)
                    )
                    row = cur.fetchone()
                    if not row:
                        return error.error_non_exist_book_id(book_id)
                    
                    # 更新价格
                    book_info = self._parse_book_info(row[0])
                    book_info['price'] = new_price
                    updated_book_json = json.dumps(book_info)
                    
                    # 更新store表
                    cur.execute(
                        "UPDATE store SET book_info = %s WHERE store_id = %s AND book_id = %s",
                        (updated_book_json, store_id, book_id)
                    )
                    
                    # 更新新的库存表和书籍目录
                    try:
                        cur.execute("""
                            UPDATE store_inventory 
                            SET price_override = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE store_id = %s AND book_id = %s
                        """, (new_price, store_id, book_id))
                        
                        cur.execute("""
                            UPDATE book_catalog 
                            SET price = %s 
                            WHERE book_id = %s
                        """, (new_price, book_id))
                    except psycopg2.Error:
                        # 如果新表不存在，忽略错误
                        pass
            
            return 200, "ok"
        
        return self._execute_with_error_handling("update_book_price", _update_price_operation)