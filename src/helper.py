from http.cookies import SimpleCookie
import time
from datetime import datetime
import os


def load_env_cookies():
    return { k:v for k,v in os.environ.items() if k.startswith('COOKIES_') and v.strip() }

def parse_cookies(cookies:str):
    c = SimpleCookie()
    c.load(cookies)
    return {k: m.value for k, m in c.items()}

def unix_ms():
    return int(time.time() * 1000)

def current_hour():
    return f'{datetime.now().hour:02}'

def rpc_weekday():
    return str(datetime.now().isoweekday())

