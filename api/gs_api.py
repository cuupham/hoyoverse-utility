from api._core_api import CoreAPI
from helper import get_hour_str, get_unix_ms, get_rpc_weekday


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

    def get_user_game_role(self):
        return self._get(
            'https://api-account-os.hoyolab.com/binding/api/getUserGameRolesByLtoken',
            headers= {
                **self.ORIGIN_TYPE['hoyolab'],
                'x-rpc-app_version': '4.0.0',
                'x-rpc-client_type': '4',
                'x-rpc-device_id': self.session.cookies.get('_MHYUUID'),
                'x-rpc-hour': get_hour_str(),
                'x-rpc-language': 'en-us',
                'x-rpc-lrsag': '',
                'x-rpc-page_info': '{"pageName":"HomeGamePage","pageType":"42","pageId":"","pageArrangement":"Hot","gameId":"6"}',
                'x-rpc-page_name': 'HomeGamePage',
                'x-rpc-show-translated': 'false',
                'x-rpc-source_info': '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
                'x-rpc-sys_version': 'Windows NT 10.0',
                'x-rpc-timezone': 'Asia/Bangkok',
                'x-rpc-weekday': get_rpc_weekday(),
            },
            params = {
                #'lang': 'en',
                'region': 'os_asia',
                'game_biz': 'hk4e_global',
                #'sLangKey': 'en-us',
            }
        )

    def get_material(self):
        return self._get(
            f'{self.BBS_URL}/circle/channel/guide/material',
            headers={
                **self.ORIGIN_TYPE['hoyolab'],
                'x-rpc-app_version': '4.0.0',
                'x-rpc-client_type': '4',
                'x-rpc-device_id': self.session.cookies['_MHYUUID'],
                'x-rpc-hour': get_hour_str(),
                'x-rpc-language': 'en-us',
                'x-rpc-lrsag': '',
                'x-rpc-page_info': '{"pageName":"","pageType":"","pageId":"","pageArrangement":"","gameId":""}',
                'x-rpc-page_name': '',
                'x-rpc-show-translated': 'false',
                'x-rpc-source_info': '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
                'x-rpc-sys_version': 'Windows NT 10.0',
                'x-rpc-timezone': 'Asia/Bangkok',
                'x-rpc-weekday': get_rpc_weekday(),
            },
            params = {
                'game_id': '2',
            }
        )

    def redeem_code(self):
        ...



    