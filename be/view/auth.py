#!/usr/bin/env python3
from flask import Blueprint, request, jsonify
from be.model import user
import logging
from typing import Tuple, Dict, Any

bp_auth = Blueprint("auth", __name__, url_prefix="/auth")
logger = logging.getLogger(__name__)

def _handle_response(code: int, message: str, data: Dict[str, Any] = None) -> Tuple[Dict[str, Any], int]:
    """统一处理响应格式"""
    response = {"message": message}
    if data:
        response.update(data)
    return jsonify(response), code

@bp_auth.route("/login", methods=["POST"])
def login() -> Tuple[Dict[str, Any], int]:
    try:
        data = request.get_json()
        if not data:
            return _handle_response(400, "请求数据为空")
            
        user_id = data.get("user_id", "")
        password = data.get("password", "")
        terminal = data.get("terminal", "")
        
        if not all([user_id, password, terminal]):
            return _handle_response(400, "缺少必要参数")
            
        u = user.User()
        code, message, token = u.login(user_id=user_id, password=password, terminal=terminal)
        return _handle_response(code, message, {"token": token} if token else None)
        
    except Exception as e:
        logger.error(f"登录失败: {str(e)}")
        return _handle_response(500, "服务器内部错误")

@bp_auth.route("/logout", methods=["POST"])
def logout() -> Tuple[Dict[str, Any], int]:
    try:
        data = request.get_json()
        if not data:
            return _handle_response(400, "请求数据为空")
            
        user_id = data.get("user_id")
        token = request.headers.get("token")
        
        if not all([user_id, token]):
            return _handle_response(400, "缺少必要参数")
            
        u = user.User()
        code, message = u.logout(user_id=user_id, token=token)
        return _handle_response(code, message)
        
    except Exception as e:
        logger.error(f"登出失败: {str(e)}")
        return _handle_response(500, "服务器内部错误")

@bp_auth.route("/register", methods=["POST"])
def register() -> Tuple[Dict[str, Any], int]:
    try:
        data = request.get_json()
        if not data:
            return _handle_response(400, "请求数据为空")
            
        user_id = data.get("user_id", "")
        password = data.get("password", "")
        
        if not all([user_id, password]):
            return _handle_response(400, "缺少必要参数")
            
        u = user.User()
        code, message = u.register(user_id=user_id, password=password)
        return _handle_response(code, message)
        
    except Exception as e:
        logger.error(f"注册失败: {str(e)}")
        return _handle_response(500, "服务器内部错误")

@bp_auth.route("/unregister", methods=["POST"])
def unregister() -> Tuple[Dict[str, Any], int]:
    try:
        data = request.get_json()
        if not data:
            return _handle_response(400, "请求数据为空")
            
        user_id = data.get("user_id", "")
        password = data.get("password", "")
        
        if not all([user_id, password]):
            return _handle_response(400, "缺少必要参数")
            
        u = user.User()
        code, message = u.unregister(user_id=user_id, password=password)
        return _handle_response(code, message)
        
    except Exception as e:
        logger.error(f"注销失败: {str(e)}")
        return _handle_response(500, "服务器内部错误")

@bp_auth.route("/password", methods=["POST"])
def change_password() -> Tuple[Dict[str, Any], int]:
    try:
        data = request.get_json()
        if not data:
            return _handle_response(400, "请求数据为空")
            
        user_id = data.get("user_id", "")
        old_password = data.get("oldPassword", "")
        new_password = data.get("newPassword", "")
        
        if not all([user_id, old_password, new_password]):
            return _handle_response(400, "缺少必要参数")
            
        u = user.User()
        code, message = u.change_password(user_id=user_id, old_password=old_password, new_password=new_password)
        return _handle_response(code, message)
        
    except Exception as e:
        logger.error(f"修改密码失败: {str(e)}")
        return _handle_response(500, "服务器内部错误")

@bp_auth.route("/search_book", methods=["POST"])
def search_book() -> Tuple[Dict[str, Any], int]:
    try:
        data = request.get_json()
        if not data:
            return _handle_response(400, "请求数据为空")
            
        title = data.get("title", "")
        content = data.get("content", "")
        tag = data.get("tag", "")
        store_id = data.get("store_id", "")
        
        u = user.User()
        code, result = u.search_book(title=title, content=content, tag=tag, store_id=store_id)
        return _handle_response(code, "ok", {"books": result})
        
    except Exception as e:
        logger.error(f"搜索图书失败: {str(e)}")
        return _handle_response(500, "服务器内部错误")