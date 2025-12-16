import requests


class BaseAPI:

    HEADERS_BASE = {
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

    ORIGIN = {
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

    PARAMS = {
        'gs': {
            'game_id': '2',
            'act_id': 'e202102251931481',
            'region': {
                'asia': 'os_asia',
                'usa': 'os_usa',
                'euro': 'os_euro',
                'tw': 'os_cht',
            },
            'game_biz': 'hk4e_global',
        },
        'sr': {
            'game_id': '6',
            'act_id': 'e202303301540311',
            'region': {
                'asia': 'prod_official_asia',
                'usa': 'prod_official_usa',
                'euro': 'prod_official_eur',
                'tw': 'prod_official_cht',
            },
            'game_biz': 'hkrpg_global'
        },
        'zzz': {
            'game_id': '8',
            'act_id': 'e202406031448091',
            'region': {
                'asia': 'prod_gf_jp',
                'usa': 'prod_gf_us',
                'euro': 'prod_gf_eu',
                'tw': 'prod_gf_sg',
            },
            'game_biz': 'nap_global'
        },
    }

    @classmethod
    def _get(cls, url:str, /, cookies:dict, headers:dict|None=None, params:dict|None=None) -> dict[str]:
        return requests.get(
            url=url,
            cookies=cookies,
            headers={
                **cls.HEADERS_BASE,
                **(headers or {})
            },   
            params=params
        ).json()
    
    @classmethod
    def _post(cls, url:str, /, cookies:dict, headers:dict, json_data:dict) -> dict[str]:
        return requests.post(
            url=url,
            cookies=cookies,
            headers={
                **cls.HEADERS_BASE,
                **headers
            },
            json=json_data
        ).json()
    








