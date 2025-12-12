from api.gs_api import GsAPI
from api.sr_api import SrAPI
from api.zzz_api import ZzzAPI

from core.utils import parse_cookies


def initialize_api(raw_cookies: dict[str, str]):
    GAME_APIS = {
        'gs': GsAPI,
        'sr': SrAPI,
        'zzz': ZzzAPI,
    }
    
    apis = {}
    for cookie_name, cookies_str in raw_cookies.items():
        parsed = parse_cookies(cookies_str)
        apis[cookie_name] = {code:cls(parsed) for code, cls in GAME_APIS.items()}
    return apis

def get_api_0(apis):
    return next(iter(apis.values()))
