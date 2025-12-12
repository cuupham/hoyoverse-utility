from http.cookies import SimpleCookie
import os
import time
from datetime import datetime


def parse_cookies(cookies_str: str) -> dict[str, str]:
    cookie = SimpleCookie()
    cookie.load(cookies_str)
    return {k: m.value for k, m in cookie.items()}

def get_unix_ms() -> int:
    return int(time.time() * 1000)

def get_cookies_env() -> dict[str, str]:
    return {
        k: v for k, v in os.environ.items()
        if k.startswith("COOKIES_") and v.strip()
    }

def get_current_hour_str() -> str:
    return f"{datetime.now().hour:02}"

def get_rpc_weekday() -> str:       
    return str(datetime.now().isoweekday())     # ISO: 1 = Monday, 7 = Sunday




