from api._core_api import CoreAPI
from helper import get_hour_str, get_unix_ms, get_rpc_weekday


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
                #'t': get_unix_ms(),
                'game_biz': 'nap_global',
                'region': 'prod_gf_jp',
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
                'game_id': '8',
            }
        )

    def redeem_code(self):
        ...

     