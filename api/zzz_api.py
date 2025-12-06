from api._core import CoreAPI
from helper import get_hour_str, get_unix_ms


class ZzzAPI(CoreAPI):
    
    def __init__(self, cookies: dict):
        super().__init__(cookies)
        self.public_url = f'{self.PUBLIC_URL}/zzz/os'

    def info(self):
        return self._get(
            f'{self.public_url}/info',
            headers={
                **self.ORIGIN_TYPE['act_hoyolab'],
                'x-rpc-signgame': 'zzz',
            },
            params = {
                'lang': 'en-us',
                'act_id': self.ACT_ID['zzz'],
            }
        )

    def checkin(self):
        return self._post(
            f'{self.public_url}/sign',
            headers={
                **self.ORIGIN_TYPE['act_hoyolab'],
                'x-rpc-client_type': '5',
                'x-rpc-platform': '4',
                'x-rpc-signgame': 'zzz',
            },
            json_data = {
                'act_id': self.ACT_ID['zzz'],
                'lang': 'en-us',
            }
        )
    
    def redeem_code(self):
        ...

        # api bi loi
        # return self._post(
        #     'https://public-operation-nap.hoyoverse.com/common/apicdkey/api/webExchangeCdkeyRisk',
        #     headers={

        #     },
        #     json_data = {
        #         't': self.unix_time,
        #         'lang': 'en',
        #         'game_biz': 'nap_global',
        #         'uid': uid,
        #         'region': 'prod_gf_jp',
        #         'cdkey': cdkey,
        #         'platform': '4',
        #         'device_uuid': self.user_cookies['_MHYUUID'],
        #     }
        # )
        


    # old code
    # def info(self):
    #     endpoint = f'{self.url}/info'
    #     headers = {
    #         **self.HEADERS_COMMON,
    #         **self.ORIGIN_TYPE['act_hoyolab'],
    #         'x-rpc-signgame': 'zzz',
    #     }
    #     cookies = self.user_cookies
    #     params = {
    #         'lang': 'en-us',
    #         'act_id': self.ACT_ID['zzz'],
    #     }
    #     return self.send_get(endpoint, headers, cookies, params)

    # def checkin(self):
    #     endpoint = f'{self.url}/sign'
    #     headers = {
    #         **self.HEADERS_COMMON,
    #         **self.ORIGIN_TYPE['act_hoyolab'],
    #         'x-rpc-client_type': '5',
    #         'x-rpc-platform': '4',
    #         'x-rpc-signgame': 'zzz',
    #     }
    #     cookies = self.user_cookies
    #     json_data = {
    #         'act_id': self.ACT_ID['zzz'],
    #         'lang': 'en-us',
    #     }
    #     return self.send_post(endpoint, headers, cookies, json_data)

    # def redeem_code(self, uid:str, cdkey:str):
    #     endpoint = 'https://public-operation-nap.hoyoverse.com/common/apicdkey/api/webExchangeCdkeyRisk'
    #     headers = {
    #         **self.HEADERS_COMMON,
    #         **self.ORIGIN_TYPE['zenless']
    #     }
    #     cookies = self.user_cookies
    #     json_data = {
    #         't': self.unix_time,
    #         'lang': 'en',
    #         'game_biz': 'nap_global',
    #         'uid': uid,
    #         'region': 'prod_gf_jp',
    #         'cdkey': cdkey,
    #         'platform': '4',
    #         'device_uuid': self.user_cookies['_MHYUUID'],
    #     }
    #     return self.send_post(endpoint, headers, cookies, json_data)
