from api._core import CoreAPI


class GsAPI(CoreAPI):
    
    def __init__(self, user_cookies):
        self.user_cookies = user_cookies

    def info(self):
        endpoint = f'{self.HK4E_URL}/info'
        headers = {
            **self.HEADERS_COMMON,
            **self.ORIGIN_TYPE['act_hoyolab'],
            'x-rpc-lrsag': '',
        }
        cookies = self.user_cookies
        params = {
            'lang': 'en-us',
            'act_id': 'e202102251931481',
        }
        return self.send_get(endpoint, headers, cookies, params)

    def checkin(self):
        endpoint = f"{self.HK4E_URL}/sign?lang=en-us"
        headers = {
            **self.HEADERS_COMMON,
            "content-type": "application/json;charset=UTF-8",
            **self.ORIGIN_TYPE['act_hoyolab'],
            'x-rpc-app_version': '',
            'x-rpc-device_id': self.user_cookies["_HYVUUID"],  # _HYVUUID
            'x-rpc-device_name': '',
            'x-rpc-lrsag': '',
            'x-rpc-platform': '4',
        }
        cookies = self.user_cookies
        json_data = {
            'act_id': 'e202102251931481',
        }
        return self.send_post(endpoint, headers, cookies, json_data)

    def redeem_code(self):
        ...