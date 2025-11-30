from api._core import CoreAPI
from helper import get_unix_ms


class ZzzAPI(CoreAPI):
    
    def __init__(self, user_cookies: dict): #, act_id: str):
        self.user_cookies = user_cookies
        self.url = f'{self.PUBLIC_URL}/zzz/os'
        #self.act_id = act_id

    @property
    def unix_time(self):
        return get_unix_ms()

    def info(self):
        endpoint = f'{self.url}/info'
        headers = {
            **self.HEADERS_COMMON,
            **self.ORIGIN_TYPE['act_hoyolab'],
            'x-rpc-signgame': 'zzz',
        }
        cookies = self.user_cookies
        params = {
            'lang': 'en-us',
            #'act_id': f'{self.act_id}',
            #'act_id': self.act_id,
            'act_id': 'e202406031448091',
        }
        return self.send_get(endpoint, headers, cookies, params)

    def checkin(self):
        endpoint = f'{self.url}/sign'
        headers = {
            **self.HEADERS_COMMON,
            **self.ORIGIN_TYPE['act_hoyolab'],
            'x-rpc-client_type': '5',
            'x-rpc-platform': '4',
            'x-rpc-signgame': 'zzz',
        }
        cookies = self.user_cookies
        json_data = {
            #'act_id': f'{self.act_id}',
            #'act_id': self.act_id,
            'act_id': 'e202406031448091',
            'lang': 'en-us',
        }
        return self.send_post(endpoint, headers, cookies, json_data)

    def redeem_code(self, uid:str, cdkey:str):
        endpoint = 'https://public-operation-nap.hoyoverse.com/common/apicdkey/api/webExchangeCdkeyRisk'
        headers = {
            **self.HEADERS_COMMON,
            # 'origin': 'https://zenless.hoyoverse.com',
            # 'referer': 'https://zenless.hoyoverse.com/',
            **self.ORIGIN_TYPE['zenless']
        }
        cookies = self.user_cookies
        json_data = {
            #'t': 1764466892170,
            't': self.unix_time,
            'lang': 'en',
            'game_biz': 'nap_global',
            #'uid': '1316327131',
            'uid': uid,
            'region': 'prod_gf_jp',
            #'cdkey': 'ZZZ24KRAMPUS',
            'cdkey': cdkey,
            'platform': '4',
            #'device_uuid': 'f749c865-07b0-4669-a348-7aed286e003f',
            'device_uuid': self.user_cookies['_MHYUUID'],
        }
        return self.send_post(endpoint, headers, cookies, json_data)
