from src.api.genshin_api import GenshinAPI as g
from src.api.star_rail_api import StarRailAPI as s
from src.api.zzz_api import ZzzAPI as z

from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict


class SignController:
    
    @staticmethod
    def _is_sign(api: g|s|z, cookies:dict):
        r = api.get_sign_info(cookies)
        if r.get('retcode') != 0:
            r = {k:r[k] for k in ('retcode', 'message')}
            raise RuntimeError(f'[/info][BAD_RETCODE]: {r}')
        data = r.get('data')
        if not isinstance(data, dict) or 'is_sign' not in data:
            raise RuntimeError(f'[/info][INVALID_DATA]: {r}')
        return data['is_sign']

    @classmethod
    def sign(cls, api: g|s|z, cookies:dict):
        try:
            is_sign = cls._is_sign(api, cookies)
            if is_sign:
                return 'Already signed-in'
        except RuntimeError as e:
            return str(e)
        
        r = api.submit_sign(cookies)
        return {k:r[k] for k in ('retcode', 'message')}
    
    @classmethod
    def _sign_task(cls, name, cookies, api, game):
        result = cls.sign(api, cookies)
        return name, game, result

    @classmethod
    def run_multi_sign(cls, user_cookies: dict):
        results = defaultdict(dict)

        with ThreadPoolExecutor(max_workers=9) as executor:
            futures = [
                executor.submit(cls._sign_task, name, cookies, api, game)
                for name, cookies in user_cookies.items()
                for api, game in (
                    (g, 'Genshin'),
                    (s, 'Star Rail'),
                    (z, 'ZZZ'),
                )
            ]

            for future in as_completed(futures):
                name, game, r = future.result()
                results[name][game] = r

        return results
