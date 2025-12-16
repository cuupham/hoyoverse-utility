from src.helper import current_hour, rpc_weekday
from src.api.base_api import BaseAPI

from typing import Literal


class HoyolabAPI(BaseAPI):

    URL_BBS_MISC = 'https://bbs-api-os.hoyolab.com/community/misc'
    URL_BBS_PAINTER = 'https://bbs-api-os.hoyolab.com/community/painter/wapi'


    @classmethod
    def get_user_brief_info(cls, cookies:dict):
        """ Check user status """
        return cls._get(
            f'{cls.URL_BBS_MISC}/wapi/account/user_brief_info',
            cookies=cookies,
            headers={
                'x-rpc-client_type': '4',
                'x-rpc-device_id': cookies['_MHYUUID'],
                'x-rpc-hour': current_hour(),
                'x-rpc-language': 'en-us',
                'x-rpc-lrsag': '',
                'x-rpc-page_info': '{"pageName":"HomePage","pageType":"","pageId":"","pageArrangement":"","gameId":""}',
                'x-rpc-page_name': 'HomePage',
                'x-rpc-show-translated': 'false',
                'x-rpc-source_info': '{"sourceName":"UserSettingPage","sourceType":"RewardsInfo","sourceId":"","sourceArrangement":"","sourceGameId":""}',
                'x-rpc-sys_version': 'Windows NT 10.0',
                'x-rpc-timezone': 'Asia/Bangkok',
                'x-rpc-weekday': rpc_weekday(),
            },
        )
    
    @classmethod
    def get_materials(cls, cookies:dict, game_choice:Literal['gs','sr','zzz']):
        """ Fetch CDKeys """
        return cls._get(
            f'{cls.URL_BBS_PAINTER}/circle/channel/guide/material',
            cookies=cookies,
            headers={
                **cls.ORIGIN['hoyolab'],
                'x-rpc-client_type': '4',
                'x-rpc-device_id': cookies['_MHYUUID'],
                'x-rpc-hour': current_hour(),
                'x-rpc-language': 'en-us',
                'x-rpc-lrsag': '',
                'x-rpc-page_info': '{"pageName":"","pageType":"","pageId":"","pageArrangement":"","gameId":""}',
                'x-rpc-page_name': '',
                'x-rpc-show-translated': 'false',
                'x-rpc-source_info': '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
                'x-rpc-sys_version': 'Windows NT 10.0',
                'x-rpc-timezone': 'Asia/Bangkok',
                'x-rpc-weekday': rpc_weekday(),
            },
            params={
                'game_id': cls.PARAMS[game_choice]['game_id'],
            }
        )
    
    @classmethod
    def get_user_game_roles(cls, cookies:dict, game_choice:Literal['gs', 'sr', 'zzz'], region_choice:Literal['asia', 'usa', 'euro', 'tw']):
        """ Get UID """
        return cls._get(
            'https://api-account-os.hoyolab.com/binding/api/getUserGameRolesByLtoken',
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
                'region': cls.PARAMS[game_choice]['region'][region_choice],
                'game_biz': cls.PARAMS[game_choice]['game_biz']
            }
        )
    
