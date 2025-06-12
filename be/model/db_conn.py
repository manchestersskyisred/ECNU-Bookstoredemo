from be.model import database

class DBConn:
    def __init__(self):
        self.conn = database.get_db_conn()

    def user_id_exist(self, user_id):
        with self.conn.cursor() as cur:
            cur.execute(
                'SELECT EXISTS(SELECT 1 FROM "user" WHERE user_id = %s);', (user_id,)
            )
            return cur.fetchone()[0]

    def book_id_exist(self, store_id, book_id):
        with self.conn.cursor() as cur:
            cur.execute(
                'SELECT EXISTS(SELECT 1 FROM store WHERE store_id = %s AND book_id = %s);',
                (store_id, book_id),
            )
            return cur.fetchone()[0]

    def store_id_exist(self, store_id):
        with self.conn.cursor() as cur:
            # 优先检查新表结构
            cur.execute(
                'SELECT EXISTS(SELECT 1 FROM store_info WHERE store_id = %s);', (store_id,)
            )
            exists_in_new = cur.fetchone()[0]
            if exists_in_new:
                return True
            
            # 向后兼容：检查旧表结构
            cur.execute(
                'SELECT EXISTS(SELECT 1 FROM user_store WHERE store_id = %s);', (store_id,)
            )
            return cur.fetchone()[0]
        
    def close(self):
        self.cur.close()
        self.conn.close()