import pymongo
import uuid
import json
import logging
import threading
import time
from typing import Dict, List, Tuple, Any, Optional, Union
from be.model import db_conn
from be.model import error


class Buyer(db_conn.DBConn):
    def __init__(self):
        super().__init__()
        self.timer = None
        self.db = self.conn

    def new_order(
            self, user_id: str, store_id: str, id_and_count: List[Tuple[str, int]]
    ) -> Tuple[int, str, str]:
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
                
            transaction_id = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))
            order_items = []
            
            for book_id, quantity in id_and_count:
                inventory_item = self.db["store"].find_one({"store_id": store_id, "book_id": book_id})
                if not inventory_item:
                    return error.error_non_exist_book_id(book_id) + (order_id,)
                    
                available_stock = inventory_item["stock_level"]
                if available_stock < quantity:
                    return error.error_stock_level_low(book_id) + (order_id,)
                    
                query_conditions = {
                    "book_id": book_id, 
                    "store_id": store_id, 
                    "stock_level": {"$gte": quantity}
                }
                stock_update = {"$inc": {"stock_level": -quantity}}
                
                update_result = self.db["store"].update_one(query_conditions, stock_update)
                if update_result.modified_count == 0:
                    return error.error_stock_level_low(book_id) + (order_id,)
                    
                book_info_json = json.loads(inventory_item["book_info"])
                item_price = book_info_json.get("price") * quantity
                
                order_item = {
                    "order_id": transaction_id,
                    "book_id": book_id,
                    "count": quantity,
                    "price": item_price
                }
                order_items.append(order_item)

            if order_items:
                self.db["new_order_detail"].insert_many(order_items)
                
            order_record = {
                "order_id": transaction_id, 
                "user_id": user_id, 
                "store_id": store_id
            }
            self.db["new_order"].insert_one(order_record)
            
            order_id = transaction_id
            self.timer = threading.Timer(10.0, self.cancel_order, args=[user_id, order_id])
            self.timer.start()
            
            history_record = order_record.copy()
            history_record["status"] = "pending"
            history_record["created_at"] = int(time.time())
            
            self.db["order_history"].insert_one(history_record)
            self.db["order_history_detail"].insert_many(order_items)

        except pymongo.errors.PyMongoError as e:
            logging.error("DB Error: {}".format(str(e)))
            return 528, str(e), ""
        except Exception as e:
            logging.info("System Error: {}".format(str(e)))
            return 530, str(e), ""

        return 200, "ok", order_id


    def payment(self, user_id: str, password: str, order_id: str) -> Tuple[int, str]:
        try:
            db = self.db
            order_record = db["new_order"].find_one({"order_id": order_id})
            if not order_record:
                return error.error_invalid_order_id(order_id)
                
            if order_record["user_id"] != user_id:
                return error.error_authorization_fail()
                
            buyer_record = db["user"].find_one({"user_id": user_id})
            if not buyer_record:
                return error.error_non_exist_user_id(user_id)
                
            if password != buyer_record["password"]:
                return error.error_authorization_fail()
                
            order_status = db["order_history"].find_one({"order_id": order_id})["status"]
            if order_status != "pending":
                error.error_invalid_order_status(order_id)
                
            if self.timer:
                self.timer.cancel()
                
            order_details = db["new_order_detail"].find({"order_id": order_id})
            total_amount = sum(item["price"] for item in order_details)
            
            if buyer_record["balance"] < total_amount:
                return error.error_not_sufficient_funds(order_id)
                
            update_result = db["user"].update_one(
                {"user_id": user_id, "balance": {"$gte": total_amount}}, 
                {"$inc": {"balance": -total_amount}}
            )
            
            if update_result.modified_count == 0:
                return error.error_not_sufficient_funds(order_id)
                
            store_owner_record = db["user_store"].find_one({"store_id": order_record["store_id"]})
            seller_id = store_owner_record["user_id"]
            
            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)
                
            seller_update = db["user"].update_one(
                {"user_id": seller_id}, 
                {"$inc": {"balance": total_amount}}
            )
            
            if seller_update.modified_count == 0:
                return error.error_non_exist_user_id(seller_id)
                
            db["new_order"].delete_one({"order_id": order_id})
            db["new_order_detail"].delete_many({"order_id": order_id})
            
            history_update = {
                "$set": {
                    "status": "paid",
                    "paid_at": int(time.time())
                }
            }
            db["order_history"].update_one({"order_id": order_id}, history_update)

        except pymongo.errors.PyMongoError as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)

        return 200, "ok"


    def add_funds(self, user_id: str, password: str, add_value: Union[int, float]) -> Tuple[int, str]:
        try:
            db = self.db
            user_record = db["user"].find_one({"user_id": user_id})
            
            if not user_record or user_record["password"] != password:
                return error.error_authorization_fail()
                
            update_result = db["user"].update_one(
                {"user_id": user_id}, 
                {"$inc": {"balance": add_value}}
            )
            
            if update_result.modified_count == 0:
                return error.error_non_exist_user_id(user_id)

        except pymongo.errors.PyMongoError as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)

        return 200, "ok"


    def get_order_history(self, user_id: str) -> Tuple[int, str, List[Dict]]:
        try:
            db = self.db
            user_record = db["user"].find_one({"user_id": user_id})
            
            if not user_record:
                return error.error_non_exist_user_id(user_id) + ([],)
            
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$lookup": {
                    "from": "order_history_detail",
                    "localField": "order_id",
                    "foreignField": "order_id",
                    "as": "order_details"
                }}
            ]
            
            order_history = db["order_history"].aggregate(pipeline)
            
            if not order_history:
                return 200, "No orders found", []

            result_list = []
            for order in order_history:
                order_details = []
                
                for detail in order["order_details"]:
                    item_info = {
                        "book_id": detail["book_id"],
                        "count": detail["count"],
                        "price": detail["price"]
                    }
                    order_details.append(item_info)
                
                order_info = {
                    "order_id": order["order_id"],
                    "order_detail": order_details,
                    "status": order.get("status", "unknown")
                }
                result_list.append(order_info)

        except pymongo.errors.PyMongoError as e:
            return 528, str(e), []
        except Exception as e:
            return 530, str(e), []

        return 200, "ok", result_list


    def cancel_order(self, user_id: str, order_id: str) -> Tuple[int, str]:
        try:
            db = self.db
            order_record = db["new_order"].find_one({"order_id": order_id})
            
            if not order_record:
                return error.error_invalid_order_id(order_id)

            if order_record["user_id"] != user_id:
                return error.error_authorization_fail()

            order_status = db["order_history"].find_one({"order_id": order_id})["status"]
            if order_status != "pending":
                return error.error_invalid_order_status(order_id)

            order_delete = db["new_order"].delete_one({"order_id": order_id})
            if order_delete.deleted_count == 0:
                return error.error_invalid_order_id(order_id)

            detail_delete = db["new_order_detail"].delete_many({"order_id": order_id})
            if detail_delete.deleted_count == 0:
                return error.error_invalid_order_id(order_id)

            history_update = {
                "$set": {
                    "status": "cancelled",
                    "cancelled_at": int(time.time())
                }
            }
            status_update = db["order_history"].update_one({"order_id": order_id}, history_update)
            
            if status_update.modified_count == 0:
                return error.error_invalid_order_id(order_id)
                
        except pymongo.errors.PyMongoError as e:
            return 528, "{}".format(str(e))
        except Exception as e:
            return 530, "{}".format(str(e))

        return 200, "ok"


    def receive_order(self, user_id: str, order_id: str) -> Tuple[int, str]:
        try:
            db = self.db
            order_record = db["order_history"].find_one({"order_id": order_id})
            
            if not order_record:
                return error.error_invalid_order_id(order_id)
                
            if order_record["user_id"] != user_id:
                return error.error_authorization_fail()
                
            if order_record["status"] != "shipped":
                return error.error_not_shipped(order_id)
                
            history_update = {
                "$set": {
                    "status": "received",
                    "received_at": int(time.time())
                }
            }
            status_update = db["order_history"].update_one({"order_id": order_id}, history_update)
            
            if status_update.modified_count == 0:
                return error.error_invalid_order_id(order_id)

        except pymongo.errors.PyMongoError as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)

        return 200, "ok"

    def collect_book(self, user_id: str, book_id: str) -> Tuple[int, str]:
        try:
            db = self.db
            user_record = db["user"].find_one({"user_id": user_id})
            
            if not user_record:
                return error.error_non_exist_user_id(user_id)

            user_collection = user_record.get("collection", [])
            if book_id in user_collection:
                return 200, "book already in collection"

            collection_update = db["user"].update_one(
                {"user_id": user_id},
                {"$addToSet": {"collection": book_id}}
            )
            
            if collection_update.modified_count == 0:
                return 529, "Failed to update collection"
                
        except pymongo.errors.PyMongoError as e:
            return 528, str(e)
        except Exception as e:
            return 530, "{}".format(str(e))
        
        return 200, "ok"


    def uncollect_book(self, user_id: str, book_id: str) -> Tuple[int, str]:
        try:
            db = self.db
            user_record = db["user"].find_one({"user_id": user_id})
            
            if not user_record:
                return error.error_non_exist_user_id(user_id)

            collection_update = db["user"].update_one(
                {"user_id": user_id},
                {"$pull": {"collection": book_id}}
            )
            
        except pymongo.errors.PyMongoError as e:
            return 528, str(e)
        except Exception as e:
            return 530, "{}".format(str(e))

        return 200, "ok"


    def get_collection(self, user_id: str) -> Tuple[int, str]:
        try:
            db = self.db
            user_record = db["user"].find_one({"user_id": user_id})
            
            if not user_record:
                return error.error_non_exist_user_id(user_id)

            book_collection = user_record.get("collection", [])
            
        except pymongo.errors.PyMongoError as e:
            return 528, str(e)
        except Exception as e:
            return 530, "{}".format(str(e))

        if not book_collection:
            return 200, "empty collection"
        else:
            return 200, book_collection


    def collect_store(self, user_id: str, store_id: str) -> Tuple[int, str]:
        try:
            db = self.db
            user_record = db["user"].find_one({"user_id": user_id})
            
            if not user_record:
                return error.error_non_exist_user_id(user_id)

            store_collection = user_record.get("store_collection", [])
            if store_id in store_collection:
                return 200, "store already in collection"

            collection_update = db["user"].update_one(
                {"user_id": user_id},
                {"$addToSet": {"store_collection": store_id}}
            )
            
            if collection_update.modified_count == 0:
                return 529, "Failed to update store collection"
                
        except pymongo.errors.PyMongoError as e:
            return 528, str(e)
        except Exception as e:
            return 530, "{}".format(str(e))

        return 200, "ok"


    def uncollect_store(self, user_id: str, store_id: str) -> Tuple[int, str]:
        try:
            db = self.db
            user_record = db["user"].find_one({"user_id": user_id})
            
            if not user_record:
                return error.error_non_exist_user_id(user_id)

            collection_update = db["user"].update_one(
                {"user_id": user_id},
                {"$pull": {"store_collection": store_id}}
            )
            
        except pymongo.errors.PyMongoError as e:
            return 528, str(e)
        except Exception as e:
            return 530, "{}".format(str(e))
        
        return 200, "ok"


    def get_store_collection(self, user_id: str) -> Tuple[int, str]:
        try:
            db = self.db
            user_record = db["user"].find_one({"user_id": user_id})
            
            if not user_record:
                return error.error_non_exist_user_id(user_id)

            store_collection = user_record.get("store_collection", [])
            
        except pymongo.errors.PyMongoError as e:
            return 528, str(e)
        except Exception as e:
            return 530, "{}".format(str(e))

        if not store_collection:
            return 200, "empty store_collection"
        else:
            return 200, store_collection