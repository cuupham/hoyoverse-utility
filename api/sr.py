from api._core import CoreAPI


class SrAPI(CoreAPI):
    
    def __init__(self, user_cookies): #, act_id: str):
        super().__init__(user_cookies)
        self.url = f'{self.PUBLIC_URL}/hkrpg/os'
        #self.act_id = act_id
    
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
            #'act_id': f'{self.act_id}',
            #'act_id': self.act_id,
            'act_id': 'e202303301540311',
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
            #'act_id': f'{self.act_id}',
            #'act_id': self.act_id,
            'act_id': 'e202303301540311',
            'lang': 'en-us',
        }
        return self.send_post(endpoint, headers, cookies, json_data)

    def claim_giftcode(self):
        ...




