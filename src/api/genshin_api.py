from src.api.base_api import BaseAPI
from src.helper import current_hour, rpc_weekday, unix_ms


class GenshinAPI(BaseAPI):

    URL_HK4E            = 'https://sg-hk4e-api.hoyolab.com/event/sol'
    URL_EXCHANGE_CDKEY  = 'https://public-operation-hk4e.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl'

    ACT_ID      = BaseAPI.PARAMS['gs']['act_id']
    GAME_BIZ    = BaseAPI.PARAMS['gs']['game_biz']

    @classmethod
    def get_sign_info(cls, cookies:dict):
        return cls._get(
            f'{cls.URL_HK4E}/info',
            cookies=cookies,
            headers={
                **cls.ORIGIN['act_hoyolab'],
                'x-rpc-lrsag': '',
            },
            params={
                'lang': 'en-us',
                'act_id': cls.ACT_ID
            }
        )
    
    @classmethod
    def submit_sign(cls, cookies:dict):
        return cls._post(
            f'{cls.URL_HK4E}/sign?lang=en-us',
            cookies=cookies,
            headers={
                "content-type": "application/json;charset=UTF-8",
                **cls.ORIGIN['act_hoyolab'],
                'x-rpc-app_version': '',
                'x-rpc-device_id': cookies["_HYVUUID"],
                'x-rpc-device_name': '',
                'x-rpc-lrsag': '',
                'x-rpc-platform': '4',
            },
            json_data={
                'act_id': cls.ACT_ID
            }
        )

    @classmethod
    def exchange_cdkey(cls, cookies, region_choice, uid, cdkey):
        return cls._get(
            cls.URL_EXCHANGE_CDKEY,
            cookies=cookies,
            headers={
                **cls.ORIGIN['hoyolab'],
                'x-rpc-client_type': '4',
                'x-rpc-device_id': cookies['_MHYUUID'],
                'x-rpc-hour': current_hour(),
                'x-rpc-language': 'en-us',
                'x-rpc-lrsag': '',
                'x-rpc-page_name': 'HomeGamePage',
                'x-rpc-show-translated': 'false',
                'x-rpc-source_info': '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
                'x-rpc-sys_version': 'Windows NT 10.0',
                'x-rpc-timezone': 'Asia/Bangkok',
                'x-rpc-weekday': rpc_weekday(),
            },
            params={
                'cdkey': cdkey,
                'game_biz': cls.GAME_BIZ,
                'lang': 'en',
                'region': cls.PARAMS['gs']['region'][region_choice],
                't': unix_ms(),
                'uid': uid
            }
        )