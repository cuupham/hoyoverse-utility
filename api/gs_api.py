from api._core import CoreAPI
from helper import get_hour_str, get_unix_ms


class GsAPI(CoreAPI):
    
    def __init__(self, cookies:dict):
        super().__init__(cookies)


    def info(self):
        return self._get(
            f'{self.HK4E_URL}/info',
            headers={
                **self.ORIGIN_TYPE['act_hoyolab'],
                'x-rpc-lrsag': '',
            },
            params = {
                'lang': 'en-us',
                'act_id': self.ACT_ID['gs'],
            }
        )

    def checkin(self):
        return self._post(
            f"{self.HK4E_URL}/sign?lang=en-us",
            headers={
                "content-type": "application/json;charset=UTF-8",
                **self.ORIGIN_TYPE['act_hoyolab'],
                'x-rpc-app_version': '',
                'x-rpc-device_id': self.session.cookies["_HYVUUID"],  # _HYVUUID
                'x-rpc-device_name': '',
                'x-rpc-lrsag': '',
                'x-rpc-platform': '4',
            },
            json_data = {
                'act_id': self.ACT_ID['gs'],
            }
        )

    def redeem_code(self):
        ...



    