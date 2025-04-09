import pymongo
import os

uri = os.getenv('MONGODB_API')

class MongoDB_client:
    __socket = None
    __database = None

    def __init__(self):
        ### 注释行为本地数据库使用 ###
        # self.socket = pymongo.MongoClient('mongodb://localhost:27017')
        self.socket = pymongo.MongoClient(uri, server_api=pymongo.server_api.ServerApi('1'))
        self.check_and_delete_database('bookstore')
        self.database = self.socket['bookstore']

    def check_and_delete_database(self, database_name):
        if database_name in self.socket.list_database_names():
            self.socket.drop_database(database_name)
            print(f"Database '{database_name}' exists. Deleted.")

    def get_db_conn(self):
        return self.database


def init_database():
    return MongoDB_client()


def get_db_conn():
    global database_instance
    return database_instance.get_db_conn() if database_instance else init_database().get_db_conn()


database_instance = init_database()