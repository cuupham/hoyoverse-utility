from src.api.base_api import BaseAPI
from src.helper import current_hour,rpc_weekday, unix_ms


class ZzzAPI(BaseAPI):

    _URL_PUBLIC         = 'https://sg-public-api.hoyolab.com/event/luna'
    URL_ZZZ             = f'{_URL_PUBLIC}/zzz/os'
    URL_EXCHANGE_CDKEY  = 'https://public-operation-nap.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl'
    
    ACT_ID      = BaseAPI.PARAMS['zzz']['act_id']
    GAME_BIZ    = BaseAPI.PARAMS['zzz']['game_biz']

    @classmethod
    def get_sign_info(cls, cookies:dict):
        return cls._get(
            f'{cls.URL_ZZZ}/info',
            cookies=cookies,
            headers={
                **cls.ORIGIN['act_hoyolab'],
                'x-rpc-signgame': 'zzz',
            },
            params = {
                'lang': 'en-us',
                'act_id': cls.ACT_ID
            }
        )

    @classmethod
    def submit_sign(cls, cookies:dict):
        return cls._post(
            f'{cls.URL_ZZZ}/sign',
            cookies=cookies,
            headers={
                **cls.ORIGIN['act_hoyolab'],
                'x-rpc-client_type': '5',
                'x-rpc-platform': '4',
                'x-rpc-signgame': 'zzz',
            },
            json_data = {
                'act_id': cls.ACT_ID,
                'lang': 'en-us',
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
                'region': cls.PARAMS['zzz']['region'][region_choice],
                't': unix_ms(),
                'uid': uid
            }
        )