from flask import Blueprint, request, jsonify
from be.model import seller
import json
from typing import Dict, Any, Tuple

# 创建蓝图，定义 URL 前缀为 "/seller"
bp_seller = Blueprint("seller", __name__, url_prefix="/seller")

def _handle_response(code: int, message: str, data: Dict[str, Any] = None) -> Tuple[Dict[str, Any], int]:
    response = {"message": message}
    if data:
        response.update(data)
    return jsonify(response), code

# 商家创建商店
@bp_seller.route("/create_store", methods=["POST"])
def seller_create_store() -> Tuple[Dict[str, Any], int]:
    try:
        data = request.get_json()
        if not data:
            return _handle_response(400, "请求数据为空")
            
        user_id = data.get("user_id", "")
        store_id = data.get("store_id", "")
        
        if not all([user_id, store_id]):
            return _handle_response(400, "缺少必要参数")
            
        s = seller.Seller()
        code, message = s.create_store(user_id, store_id)
        return _handle_response(code, message)
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")


# 商家添加图书到商店
@bp_seller.route("/add_book", methods=["POST"])
def seller_add_book() -> Tuple[Dict[str, Any], int]:
    try:
        data = request.get_json()
        if not data:
            return _handle_response(400, "请求数据为空")
            
        user_id = data.get("user_id", "")
        store_id = data.get("store_id", "")
        book_info = data.get("book_info", {})
        stock_level = int(data.get("stock_level", 0))
        
        if not all([user_id, store_id, book_info]):
            return _handle_response(400, "缺少必要参数")
            
        s = seller.Seller()
        code, message = s.add_book(
            user_id, store_id, book_info.get("id"), json.dumps(book_info), stock_level
        )
        return _handle_response(code, message)
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")


# 商家增加图书库存
@bp_seller.route("/add_stock_level", methods=["POST"])
def add_stock_level() -> Tuple[Dict[str, Any], int]:
    try:
        data = request.get_json()
        if not data:
            return _handle_response(400, "请求数据为空")
            
        user_id = data.get("user_id", "")
        store_id = data.get("store_id", "")
        book_id = data.get("book_id", "")
        add_num = int(data.get("add_stock_level", 0))
        
        if not all([user_id, store_id, book_id]):
            return _handle_response(400, "缺少必要参数")
            
        s = seller.Seller()
        code, message = s.add_stock_level(user_id, store_id, book_id, add_num)
        return _handle_response(code, message)
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")


# 商家发货
@bp_seller.route("/ship_order", methods=["POST"])
def ship_order() -> Tuple[Dict[str, Any], int]:
    try:
        data = request.get_json()
        if not data:
            return _handle_response(400, "请求数据为空")
            
        user_id = data.get("user_id", "")
        store_id = data.get("store_id", "")
        order_id = data.get("order_id", "")
        
        if not all([user_id, store_id, order_id]):
            return _handle_response(400, "缺少必要参数")
            
        s = seller.Seller()
        code, message = s.ship_order(user_id, store_id, order_id)
        return _handle_response(code, message)
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")
