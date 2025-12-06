from http.cookies import SimpleCookie
import os
import time
from datetime import datetime


def parse_cookies(cookies_str: str):
    c = SimpleCookie()
    c.load(cookies_str)
    c_dict = {key:morsel.value for key, morsel in c.items()}
    return c_dict

def get_unix_ms():
    return int(time.time() * 1000)

def cookies_env():
    return {k: v for k, v in os.environ.items() if k.startswith("COOKIES_")}

def get_hour_str() -> str:
    return f'{datetime.now().hour:02}'




