import requests


class CoreAPI:

    # --- URL ---
    BBS_URL     = 'https://bbs-api-os.hoyolab.com/community/painter/wapi'
    HK4E_URL    = "https://sg-hk4e-api.hoyolab.com/event/sol"
    PUBLIC_URL  = "https://sg-public-api.hoyolab.com/event/luna"

    # --- HEADERS ---
    HEADERS_COMMON = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9,vi-VN;q=0.8,vi;q=0.7",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "dnt": "1",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    # --- ORIGIN ---
    ORIGIN_TYPE = {
        "hoyolab": {
            "origin": "https://www.hoyolab.com",
            "referer": "https://www.hoyolab.com/",
        },
        "act_hoyolab": {
            "origin": "https://act.hoyolab.com",
            "referer": "https://act.hoyolab.com/",
        },
        "zenless": {
            "origin": "https://zenless.hoyoverse.com",
            "referer": "https://zenless.hoyoverse.com/",
        },
        "genshin": {
            'origin': 'https://genshin.hoyoverse.com',
            'referer': 'https://genshin.hoyoverse.com/',
        }
    }

    # --- ACT ---
    ACT_ID = {
        'gs': 'e202102251931481',
        'sr': 'e202303301540311',
        'zzz': 'e202406031448091',
    }

    def  __init__(self, cookies: dict):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS_COMMON)
        self.session.cookies.update(cookies)

    def _get(self, url:str, /, headers:dict, params:dict) -> dict:
        r = self.session.get(url=url, headers=headers, params=params)
        return r.json()
    
    def _post(self, url:str, /, headers:dict, json_data:dict) -> dict:
        r = self.session.post(url=url, headers=headers, json=json_data)
        return r.json()
