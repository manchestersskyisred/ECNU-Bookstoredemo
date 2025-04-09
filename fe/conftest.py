import requests
import threading
import time
from urllib.parse import urljoin
from be import serve
from fe import conf
from data import load

thread: threading.Thread = None


# 修改这里启动后端程序，如果不需要可删除这行代码
def run_backend():
    # rewrite this if rewrite backend
    serve.be_run()


def pytest_configure(config):
    global thread
    print("frontend begin test")
    thread = threading.Thread(target=run_backend)
    thread.start()
    load.load_books(conf.Use_Large_DB)
    time.sleep(3)


def pytest_unconfigure(config):
    url = urljoin(conf.URL, "shutdown")
    requests.get(url)
    thread.join()
    print("frontend end test")
