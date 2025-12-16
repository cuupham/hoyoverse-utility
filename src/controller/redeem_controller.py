from src.api.genshin_api import GenshinAPI as g
from src.api.star_rail_api import StarRailAPI as s
from src.api.zzz_api import ZzzAPI as z
from src.api.hoyolab_api import HoyolabAPI as h

from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class RedeemController:

    @staticmethod
    def fetch_cdkeys(cookies:dict, game_choice):
        r = h.get_materials(cookies, game_choice)

        if r.get('retcode') != 0:
            raise RuntimeError(f'[/material][BAD_RETCODE]: {r}')
        
        return [
            bonus['exchange_code']
            for module in r.get('data', {}).get('modules', [])
            if (group := module.get('exchange_group'))
            for bonus in group.get('bonuses', [])
            if bonus.get('exchange_code')
        ]

    @classmethod
    def fetch_multi_cdkeys(cls, cookies) -> dict[str, list[str]]:       
        all_game = ('gs', 'sr', 'zzz') 
        results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(cls.fetch_cdkeys, cookies, game): game
                for game in all_game
            }

            for future in as_completed(futures):
                game = futures[future]

                if cdkeys := future.result():
                    results[game] = cdkeys
        
        if not any(results.values()):
            raise RuntimeError("There are no CDKeys available for any game.")

        return results

    @staticmethod
    def fetch_uid(cookies: dict, game, server):
        r = h.get_user_game_roles(cookies, game, server)

        if r.get('retcode') != 0:
            raise RuntimeError(f'[/user_game...][BAD_RETCODE]: {r}')

        try:
            uid = r['data']['list'][0].get('game_uid')
        except (KeyError, IndexError):
            return None

        return uid

    @classmethod
    def fetch_multi_uid(cls, user_cookies) -> dict[str, dict[tuple[str], str]]:
        all_game = ('gs', 'sr', 'zzz')
        all_server = ('asia', 'usa', 'euro', 'tw')

        results = {}
        futures = {}

        with ThreadPoolExecutor() as executor:
            for name, cookies in user_cookies.items():
                for game in all_game:
                    for server in all_server:
                        fut = executor.submit(
                            cls.fetch_uid, cookies, game, server
                        )
                        futures[fut] = (name, game, server)

            for fut in as_completed(futures):
                name, game, server = futures[fut]
                uid = fut.result()

                if uid:
                    results.setdefault(name, {})[(game, server)] = uid
        
        if not results:
            raise RuntimeError('No UID found for any account, game, or server.')

        return results
    
    @staticmethod
    def redeem_code(api: g|s|z, cookies, cdkeys:list, uid, server):
        results = []

        for key in cdkeys:
            r = api.exchange_cdkey(cookies,server,uid,key)
            results.append((key, r))
            if key != cdkeys[-1]:
                time.sleep(5)
        
        return results
    
    @classmethod
    def redeem_multi_code(cls, user_cookies: dict, multi_cdkeys, multi_uid):
        results = {}
        futures = {}

        api_map = {
            'gs': g,
            'sr': s,
            'zzz': z,
        }

        with ThreadPoolExecutor() as executor:
            for name, cookies in user_cookies.items():
                for (game, server), uid in multi_uid.get(name, {}).items():
                    cdkeys = multi_cdkeys.get(game)
                    if not cdkeys:
                        continue

                    api = api_map[game]
                    fut = executor.submit(
                        cls.redeem_code,
                        api,
                        cookies,
                        cdkeys,
                        uid,
                        server
                    )
                    futures[fut] = (name, game, server)

            for fut in as_completed(futures):
                name, game, server = futures[fut]
                results.setdefault(name, {})[(game, server)] = fut.result()
        
        return results

