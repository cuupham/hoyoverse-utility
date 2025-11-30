import requests


class CoreAPI:

    # --- URL ---
    BBS_URL = 'https://bbs-api-os.hoyolab.com/community/painter/wapi'
    HK4E_URL = "https://sg-hk4e-api.hoyolab.com/event/sol"
    PUBLIC_URL = "https://sg-public-api.hoyolab.com/event/luna"

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
    }

    def send_get(self, endpoint, headers, cookies, params) -> dict:
        response = requests.get(url=endpoint, headers=headers, cookies=cookies, params=params)
        return response.json()

    def send_post(self, endpoint, headers, cookies, json_data) -> dict:
        response = requests.post(url=endpoint, headers=headers, cookies=cookies, json=json_data)
        return response.json()