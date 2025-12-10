from api._core_api import CoreAPI
from core.utils import get_current_hour_str, get_unix_ms, get_rpc_weekday


class SrAPI(CoreAPI):
    
    def __init__(self, cookies:dict):
        super().__init__(cookies)
        self.public_url = f'{self.PUBLIC_URL}/hkrpg/os'

    def get_sign_info(self):
        return self._get(
            f'{self.public_url}/info',
            headers= {
                 **self.ORIGIN_TYPE['act_hoyolab'],
                'x-rpc-signgame': 'hkrpg',
            },
            params = {
                'lang': 'en-us',
                'act_id': self.ACT_ID['sr'],
            }
        )
    
    def sign(self):
        return self._post(
            f'{self.public_url}/sign',
            headers= {
                **self.ORIGIN_TYPE['act_hoyolab'],
                'x-rpc-client_type': '5',
                'x-rpc-platform': '4',
                'x-rpc-signgame': 'hkrpg',
            },
            json_data = {
                'act_id': self.ACT_ID['sr'],
                'lang': 'en-us',
            }
        )
    
    def get_user_game_roles_by_ltoken(self):
        return self._get(
            'https://api-account-os.hoyolab.com/binding/api/getUserGameRolesByLtoken',
            headers= {
                **self.ORIGIN_TYPE['hoyolab'],
                #'x-rpc-app_version': '4.0.0',
                'x-rpc-client_type': '4',
                'x-rpc-device_id': self.session.cookies['_MHYUUID'],
                'x-rpc-hour': get_current_hour_str(),
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
                'game_biz': 'hkrpg_global',
                'region': 'prod_official_asia',
            }
        )

    def fetch_channel_materials(self):
        return self._get(
            self.BBS_URL + '/circle/channel/guide/material',
            headers={
                **self.ORIGIN_TYPE['hoyolab'],
                #'x-rpc-app_version': '4.0.0',
                'x-rpc-client_type': '4',
                'x-rpc-device_id': self.session.cookies['_MHYUUID'],
                'x-rpc-hour': get_current_hour_str(),
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
                'game_id': '6',
            }
        )
    
    def exchange_cdkey(self, uid_info:dict, cdkey:str):
        return self._get(
            'https://public-operation-hkrpg.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl',
            headers= {
                **self.ORIGIN_TYPE['hoyolab'],
                #'x-rpc-app_version': '4.0.0',
                'x-rpc-client_type': '4',
                'x-rpc-device_id': self.session.cookies['_MHYUUID'],
                'x-rpc-hour': get_current_hour_str(),
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
                'cdkey': cdkey,
                'game_biz': uid_info['game_biz'],
                'lang': 'en',
                'region': uid_info['region'],
                't': get_unix_ms(),
                'uid': uid_info['game_uid'],
            }
        )




