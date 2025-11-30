from http.cookies import SimpleCookie
import os
import time


def cookies_to_dict(cookies_str: str):
    c = SimpleCookie()
    c.load(cookies_str)
    c_dict = {key:morsel.value for key, morsel in c.items()}
    return c_dict

# def extract_cookies(cookies: dict):
#     raw = ('mi18nLang', '_HYVUUID', '_HYVUUID', 'ltoken_v2', 'ltmid_v2', 'ltuid_v2')
#     cookies_dict = cookies_to_dict(cookies)
#     return {k:v for k, v in cookies_dict.items() if k in raw}

def get_unix_ms():
    return int(time.time() * 1000)

def get_all_cookies_env():
    return {k: v for k, v in os.environ.items() if k.startswith("COOKIES_")}
