from src.api.hoyolab_api import HoyolabAPI as h
from src.helper import parse_cookies, load_env_cookies

from concurrent.futures import ThreadPoolExecutor, as_completed


def _is_cookie_valid(cookies:dict):
    r = h.get_user_brief_info(cookies)
    retcode = r['retcode']
    if retcode == 0 and r.get('data', None).get('email_mask', ''):
        return True
    return False

def _check_cookies(name:str, raw:str):
    cookies = parse_cookies(raw)
    if _is_cookie_valid(cookies):
        return name, cookies
    return None

class CookiesController:
    
    @staticmethod
    def require_env_cookies():
        c = load_env_cookies()
        if not c:
            raise ValueError("No cookies found in environment variables.")
        return c

    @staticmethod
    def collect_valid_env_cookies(env_cookies:dict):
        _dict = {}

        with ThreadPoolExecutor(max_workers=min(5, len(env_cookies) or 1)) as executor:
            for future in as_completed(
                executor.submit(_check_cookies, name, raw)
                for name, raw in env_cookies.items()
            ):
                result = future.result()
                if result:
                    name, cookie = result
                    _dict[name] = cookie
        
        if not _dict:
            raise ValueError('No valid cookies found')

        return _dict