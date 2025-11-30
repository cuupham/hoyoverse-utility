from api._core import CoreAPI


class SrAPI(CoreAPI):
    
    def __init__(self, user_cookies): 
        self.user_cookies = user_cookies
        self.url = f'{self.PUBLIC_URL}/hkrpg/os'
    
    def info(self):
        endpoint = f'{self.url}/info'
        headers = {
            **self.HEADERS_COMMON,
            **self.ORIGIN_TYPE['act_hoyolab'],
            'x-rpc-signgame': 'hkrpg',
        }
        cookies = self.user_cookies
        params = {
            'lang': 'en-us',
            'act_id': self.ACT_ID['sr'],
        }
        return self.send_get(endpoint, headers, cookies, params)

    def checkin(self):
        endpoint = f'{self.url}/sign'
        headers = {
            **self.HEADERS_COMMON,
            **self.ORIGIN_TYPE['act_hoyolab'],
            'x-rpc-client_type': '5',
            'x-rpc-platform': '4',
            'x-rpc-signgame': 'hkrpg',
        }
        cookies = self.user_cookies
        json_data = {
            'act_id': self.ACT_ID['sr'],
            'lang': 'en-us',
        }
        return self.send_post(endpoint, headers, cookies, json_data)

    def redeem_code(self):
        ...




