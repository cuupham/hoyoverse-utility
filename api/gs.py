from api._core import CoreAPI


class GsAPI(CoreAPI):
    
    def __init__(self, user_cookies): #, act_id: str):
        super().__init__(user_cookies)
        #self.act_id = act_id

    def info(self):
        endpoint = f'{self.HK4E_URL}/info'
        headers = {
            **self.HEADERS_COMMON,
            # "origin": "https://act.hoyolab.com",
            # "referer": "https://act.hoyolab.com/",
            **self.ORIGIN_TYPE['act_hoyolab'],
            'x-rpc-lrsag': '',
        }
        cookies = self.user_cookies
        params = {
            'lang': 'en-us',
            #'act_id': f'{self.act_id}',
            #'act_id': self.act_id,
            'act_id': 'e202102251931481',
        }

        return self.send_get(endpoint, headers, cookies, params)

    def checkin(self):
        endpoint = f"{self.HK4E_URL}/sign?lang=en-us"
        headers = {
            **self.HEADERS_COMMON,
            "content-type": "application/json;charset=UTF-8",
            # "origin": "https://act.hoyolab.com",
            # "referer": "https://act.hoyolab.com/",
            **self.ORIGIN_TYPE['act_hoyolab'],
            'x-rpc-app_version': '',
            #'x-rpc-device_id': f'{self.user_cookies["_HYVUUID"]}',  # _HYVUUID
            'x-rpc-device_id': self.user_cookies["_HYVUUID"],  # _HYVUUID
            'x-rpc-device_name': '',
            'x-rpc-lrsag': '',
            'x-rpc-platform': '4',
        }
        cookies = self.user_cookies
        json_data = {
            #"act_id":f"{self.act_id}"
            #"act_id": self.act_id
            'act_id': 'e202102251931481',
        }
        return self.send_post(endpoint, headers, cookies, json_data)

    def claim_giftcode(self):
        ...