from concurrent.futures import ThreadPoolExecutor, as_completed

import time


def fetch_cdkeys(api):
    response = api.fetch_channel_materials()
    retcode = response['retcode']

    if retcode != 0:
        raise RuntimeError(f'Request "/materials" FAILED. Detail: {response}')

    cdkeys = []
    for module in response['data']['modules']:
        if not (group := module['exchange_group']):
            continue
        for bonus in group['bonuses']:
            if code := bonus.get('exchange_code'):
                cdkeys.append(code)
    return cdkeys

def fetch_all_cdkeys(api_0: dict):
    print(' CDKEYS '.center(60, '='))

    results = {}

    with ThreadPoolExecutor(max_workers=len(api_0)) as executor:
        futures = {executor.submit(fetch_cdkeys, api): game for game, api in api_0.items()}

        for future in as_completed(futures):
            game = futures[future]

            try:
                if cdkeys := future.result():
                    results[game] = cdkeys
            except RuntimeError as e:
                print(f'[{game}]: {e}')

    if not any(results.values()):
        raise LookupError('"No cdkeys" found in any game. Exiting.')
    
    return results

def fetch_uid(api):
    response = api.get_user_game_roles_by_ltoken()
    retcode = response['retcode']

    if retcode != 0:
        raise RuntimeError(f'Request "/getUserGameRolesByLtoken" FAILED. Detail: {response}')
    
    items = response.get("data", {}).get("list", [])
    if not items or not items[0].get("game_uid"):
        return None

    it = items[0]
    return {
        "game_uid": it["game_uid"],
        "game_biz": it["game_biz"],
        "region": it["region"]
    }

def fetch_all_uid(apis: dict, target_games: tuple):
    uid_dict = {}
    futures = {}

    with ThreadPoolExecutor() as executor:
        for acc_name, api_dict in apis.items():
            for game, api in api_dict.items():
                if game in target_games:
                    futures[executor.submit(fetch_uid, api)] = (acc_name, game, api)
        
        for future in as_completed(futures):
            acc_name, game, api = futures[future]
            try:
                if uid := future.result():
                    uid_dict.setdefault(acc_name, {})[game] = (uid, api)
            except RuntimeError as e:
                print(f'[{acc_name}][{game}]: {e}')

    if not any(uid_dict.values()):
        raise LookupError('"No UID" found for any game. Exiting.')

    return uid_dict


def redeem_codes(api, cdkeys:list, uid_info:dict):
    result = []
    for index, key in enumerate(cdkeys):
        response = api.exchange_cdkey(uid_info, key)
        result.append((key, response))
        if index < len(cdkeys) -1:
            time.sleep(5)
    return result

def redeem_all_codes(all_uid: dict, all_cdkeys: dict):
    results = {}
    futures = {}

    with ThreadPoolExecutor(max_workers=25) as executor:
        for acc_name, api_dict in all_uid.items():
            for game_code, (uid_info, api) in api_dict.items():
                if game_code not in all_cdkeys:
                    continue
                futures[executor.submit(redeem_codes, api, all_cdkeys[game_code], uid_info)] = (acc_name, game_code)

        for future in as_completed(futures):
            acc_name, game_code = futures[future]
            try:
                res = future.result()
            except Exception as e:
                res = [{"error": str(e)}]

            results.setdefault(acc_name, {})[game_code] = res

    return results

def run_redeem_all(apis: dict, all_cdkeys:dict):
    target_games = tuple(all_cdkeys.keys())
    all_uid = fetch_all_uid(apis, target_games)
    res = redeem_all_codes(all_uid, all_cdkeys)

    for acc_name, game_dict in res.items():
        print(f' {acc_name} '.center(60, '╍'))
        for game_name, code_list in game_dict.items():
            print(f'[{game_name}]')
            for code, response in code_list:
                print(f'"{code}": {response}')


                