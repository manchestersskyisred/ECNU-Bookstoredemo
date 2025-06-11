 #!/usr/bin/env python3

import sys
sys.path.append('.')

from be.model.buyer import Buyer
from be.model.seller import Seller
from be.model.database import init_database
import uuid

def debug_ship_receive():
    print("=== 发货收货调试 ===")
    
    # 初始化数据库
    init_database()
    
    # 创建测试用户和订单
    buyer = Buyer()
    seller = Seller()
    
    user_id = f"test_user_{uuid.uuid1()}"
    seller_id = f"test_seller_{uuid.uuid1()}"
    store_id = f"test_store_{uuid.uuid1()}"
    
    print(f"用户ID: {user_id}")
    print(f"卖家ID: {seller_id}")
    print(f"商店ID: {store_id}")
    
    # 模拟创建用户
    with buyer.conn.cursor() as cur:
        cur.execute('INSERT INTO "user" (user_id, password, balance) VALUES (%s, %s, %s)', 
                   (user_id, "123", 1000.0))
        cur.execute('INSERT INTO "user" (user_id, password, balance) VALUES (%s, %s, %s)', 
                   (seller_id, "123", 0.0))
        buyer.conn.commit()
    
    # 创建商店
    code, msg = seller.create_store(seller_id, store_id)
    print(f"创建商店结果: {code}, {msg}")
    
    # 添加书籍
    book_info = '{"title": "测试书籍", "price": 10}'
    code, msg = seller.add_book(seller_id, store_id, "test_book_1", book_info, 10)
    print(f"添加书籍结果: {code}, {msg}")
    
    # 创建订单
    code, msg, order_id = buyer.new_order(user_id, store_id, [("test_book_1", 1)])
    print(f"创建订单结果: {code}, {msg}, 订单ID: {order_id}")
    
    if code != 200:
        print(f"创建订单失败: {msg}")
        return
    
    # 支付订单
    code, msg = buyer.payment(user_id, "123", order_id)
    print(f"支付订单结果: {code}, {msg}")
    
    if code != 200:
        print(f"支付失败: {msg}")
        return
    
    # 检查订单状态
    with buyer.conn.cursor() as cur:
        cur.execute("SELECT status FROM order_history WHERE order_id = %s", (order_id,))
        status = cur.fetchone()
        print(f"支付后订单状态: {status[0] if status else '未找到'}")
    
    # 直接测试更新语句
    print(f"\n=== 直接测试数据库更新 ===")
    with seller.conn.cursor() as cur:
        # 检查当前状态
        cur.execute("SELECT status, store_id FROM order_history WHERE order_id = %s", (order_id,))
        row = cur.fetchone()
        print(f"更新前: 状态={row[0]}, 商店={row[1]}")
        
        # 尝试更新
        cur.execute("UPDATE order_history SET status = 'shipped' WHERE order_id = %s AND status = 'paid'", (order_id,))
        print(f"更新影响行数: {cur.rowcount}")
        
        # 检查更新后状态
        cur.execute("SELECT status FROM order_history WHERE order_id = %s", (order_id,))
        status = cur.fetchone()
        print(f"更新后状态: {status[0] if status else '未找到'}")
        
        # 提交事务
        seller.conn.commit()
        
        # 再次检查
        cur.execute("SELECT status FROM order_history WHERE order_id = %s", (order_id,))
        status = cur.fetchone()
        print(f"提交后状态: {status[0] if status else '未找到'}")
    
    # 发货
    print("\n=== 第一次发货 ===")
    code, msg = seller.ship_order(seller_id, store_id, order_id)
    print(f"发货结果: {code}, {msg}")
    
    # 检查订单状态
    with buyer.conn.cursor() as cur:
        cur.execute("SELECT status FROM order_history WHERE order_id = %s", (order_id,))
        status = cur.fetchone()
        print(f"发货后订单状态: {status[0] if status else '未找到'}")
    
    # 重复发货 (应该失败)
    print("\n=== 重复发货 ===")
    code, msg = seller.ship_order(seller_id, store_id, order_id)
    print(f"重复发货结果: {code}, {msg} (应该不是200)")
    
    # 收货
    print("\n=== 收货 ===")
    code, msg = buyer.receive_order(user_id, order_id)
    print(f"收货结果: {code}, {msg}")
    
    # 检查订单状态
    with buyer.conn.cursor() as cur:
        cur.execute("SELECT status FROM order_history WHERE order_id = %s", (order_id,))
        status = cur.fetchone()
        print(f"收货后订单状态: {status[0] if status else '未找到'}")

if __name__ == "__main__":
    debug_ship_receive()