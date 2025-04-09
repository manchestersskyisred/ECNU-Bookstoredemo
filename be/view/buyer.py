from flask import Blueprint, request, jsonify, Response
from typing import Dict, Any, Tuple, List, Optional
from be.model.buyer import Buyer
import datetime

bp_buyer = Blueprint("buyer", __name__, url_prefix="/buyer")

def _handle_response(code: int, msg: str, extra_data: Dict[str, Any] = None) -> Tuple[Response, int]:
    result = {"message": msg}
    if extra_data:
        result.update(extra_data)
    return jsonify(result), code

@bp_buyer.route("/new_order", methods=["POST"])
def new_order() -> Tuple[Response, int]:
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id", "")
        store_id = data.get("store_id", "")
        books_data = data.get("books", [])
        
        if not all([user_id, store_id, books_data]):
            return _handle_response(400, "缺少必要参数")
        
        purchase_items = [(item.get("id"), item.get("count")) for item in books_data]
        
        buyer_svc = Buyer()
        status_code, result_msg, order_id = buyer_svc.new_order(user_id, store_id, purchase_items)
        return _handle_response(status_code, result_msg, {"order_id": order_id})
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")

@bp_buyer.route("/payment", methods=["POST"])
def payment() -> Tuple[Response, int]:
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id", "")
        order_id = data.get("order_id", "")
        password = data.get("password", "")
        
        if not all([user_id, order_id, password]):
            return _handle_response(400, "缺少必要参数")
        
        buyer_svc = Buyer()
        status_code, result_msg = buyer_svc.payment(user_id, password, order_id)
        return _handle_response(status_code, result_msg)
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")

@bp_buyer.route("/add_funds", methods=["POST"])
def add_funds() -> Tuple[Response, int]:
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id", "")
        password = data.get("password", "")
        add_value = int(data.get("add_value", 0))
        
        if not all([user_id, password]):
            return _handle_response(400, "缺少必要参数")
        
        buyer_svc = Buyer()
        status_code, result_msg = buyer_svc.add_funds(user_id, password, add_value)
        return _handle_response(status_code, result_msg)
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")

@bp_buyer.route("/get_order_history", methods=["POST"])
def get_order_history() -> Tuple[Response, int]:
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id", "")
        
        if not user_id:
            return _handle_response(400, "缺少必要参数")
        
        buyer_svc = Buyer()
        status_code, result_msg, orders = buyer_svc.get_order_history(user_id)
        return _handle_response(status_code, result_msg, {"orders": orders})
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")

@bp_buyer.route("/cancel_order", methods=["POST"])
def cancel_order() -> Tuple[Response, int]:
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id", "")
        order_id = data.get("order_id", "")
        
        if not all([user_id, order_id]):
            return _handle_response(400, "缺少必要参数")
        
        buyer_svc = Buyer()
        status_code, result_msg = buyer_svc.cancel_order(user_id, order_id)
        return _handle_response(status_code, result_msg)
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")

@bp_buyer.route("/receive_order", methods=["POST"])
def receive_order() -> Tuple[Response, int]:
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id", "")
        order_id = data.get("order_id", "")
        
        if not all([user_id, order_id]):
            return _handle_response(400, "缺少必要参数")
        
        buyer_svc = Buyer()
        status_code, result_msg = buyer_svc.receive_order(user_id, order_id)
        return _handle_response(status_code, result_msg)
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")

@bp_buyer.route("/get_collection", methods=["POST"])
def get_collection() -> Tuple[Response, int]:
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id", "")
        
        if not user_id:
            return _handle_response(400, "缺少必要参数")
        
        buyer_svc = Buyer()
        status_code, result_data = buyer_svc.get_collection(user_id=user_id)
        
        if status_code != 200:
            return _handle_response(status_code, result_data)
        
        return _handle_response(status_code, "获取收藏成功", {"collection": result_data})
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")

@bp_buyer.route("/collect_book", methods=["POST"])
def collect_book() -> Tuple[Response, int]:
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id", "")
        book_id = data.get("book_id", "")
        
        if not all([user_id, book_id]):
            return _handle_response(400, "缺少必要参数")
        
        buyer_svc = Buyer()
        status_code, result_msg = buyer_svc.collect_book(user_id=user_id, book_id=book_id)
        return _handle_response(status_code, result_msg)
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")

@bp_buyer.route("/uncollect_book", methods=["POST"])
def uncollect_book() -> Tuple[Response, int]:
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id", "")
        book_id = data.get("book_id", "")
        
        if not all([user_id, book_id]):
            return _handle_response(400, "缺少必要参数")
        
        buyer_svc = Buyer()
        status_code, result_msg = buyer_svc.uncollect_book(user_id=user_id, book_id=book_id)
        return _handle_response(status_code, result_msg)
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")

@bp_buyer.route("/get_store_collection", methods=["POST"])
def get_store_collection() -> Tuple[Response, int]:
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id", "")
        
        if not user_id:
            return _handle_response(400, "缺少必要参数")
        
        buyer_svc = Buyer()
        status_code, result_data = buyer_svc.get_store_collection(user_id=user_id)
        
        if status_code != 200:
            return _handle_response(status_code, result_data)
        
        return _handle_response(status_code, "获取店铺收藏成功", {"collection": result_data})
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")

@bp_buyer.route("/collect_store", methods=["POST"])
def collect_store() -> Tuple[Response, int]:
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id", "")
        store_id = data.get("store_id", "")
        
        if not all([user_id, store_id]):
            return _handle_response(400, "缺少必要参数")
        
        buyer_svc = Buyer()
        status_code, result_msg = buyer_svc.collect_store(user_id=user_id, store_id=store_id)
        return _handle_response(status_code, result_msg)
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")

@bp_buyer.route("/uncollect_store", methods=["POST"])
def uncollect_store() -> Tuple[Response, int]:
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id", "")
        store_id = data.get("store_id", "")
        
        if not all([user_id, store_id]):
            return _handle_response(400, "缺少必要参数")
        
        buyer_svc = Buyer()
        status_code, result_msg = buyer_svc.uncollect_store(user_id=user_id, store_id=store_id)
        return _handle_response(status_code, result_msg)
        
    except Exception as e:
        return _handle_response(500, "服务器内部错误")
