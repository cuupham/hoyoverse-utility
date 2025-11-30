from api._core import CoreAPI
from urllib.parse import urlparse, parse_qs


class HoyoverseAPI(CoreAPI):

    def __init__(self, user_cookies: dict):
        self.user_cookies = user_cookies

    # --- API ---
    def info_with_channel(self):
        endpoint = f"{self.BBS_URL}/circle/info"
        headers = {
            **self.HEADERS_COMMON,
            # 'origin': 'https://www.hoyolab.com',
            # 'referer': 'https://www.hoyolab.com/',
            **self.ORIGIN_TYPE['hoyolab'],
            'x-rpc-app_version': '4.0.0',
            'x-rpc-client_type': '4',
            #'x-rpc-device_id': f'{self.user_cookies["_MHYUUID"]}',   # _MHYUUID
            'x-rpc-device_id': self.user_cookies["_MHYUUID"],   # _MHYUUID
            'x-rpc-hour': '19',
            'x-rpc-language': 'en-us',
            'x-rpc-lrsag': '',
            'x-rpc-page_info': '{"pageName":"","pageType":"","pageId":"","pageArrangement":"","gameId":""}',
            'x-rpc-page_name': '',
            'x-rpc-show-translated': 'false',
            'x-rpc-source_info': '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
            'x-rpc-sys_version': 'Windows NT 10.0',
            'x-rpc-timezone': 'Asia/Bangkok',
            'x-rpc-weekday': '6',
        }
        cookies = self.user_cookies
        params = {'with_channel': '1',}
        return self.send_get(endpoint, headers, cookies, params)

    # --- Helper ---
    # @staticmethod
    # def extract_act_ids(data: dict):
    #     target_games = ('Genshin Impact', 'Honkai: Star Rail', 'Zenless Zone Zero')

    #     result = {name:None for name in target_games}

    #     game_list = data.get('data', {}).get('game_list', [])

    #     for game in game_list:
    #         name = game.get('name')
            
    #         if name not in target_games:
    #             continue

    #         for tool in game.get('tool', []):            
    #             tool_name = tool.get("name", "").lower().replace("-", "").replace(" ", "")
    #             if tool_name != "checkin":
    #                 continue

    #             web_path = tool.get('web_path') or ""
    #             parsed = urlparse(web_path)
    #             qs = parse_qs(parsed.query)

    #             act_id_list = qs.get("act_id")
    #             if act_id_list:
    #                 result[name] = act_id_list[0]
    #                 break

    #     return result