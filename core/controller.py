from api.gs_api import GsAPI
from api.sr_api import SrAPI
from api.zzz_api import ZzzAPI
from core.utils import parse_cookies
import time
from concurrent.futures import ThreadPoolExecutor


# --- ACCOUNT ---
def get_accounts(cookies_raw:dict[str, str]) -> dict[str, dict[str, GsAPI|SrAPI|ZzzAPI]]:
    accounts = {}
    for name, raw_cookie in cookies_raw.items():
        parsed = parse_cookies(raw_cookie)

        accounts[name] = {
            "gs":  GsAPI(parsed),
            "sr":  SrAPI(parsed),
            "zzz": ZzzAPI(parsed),
        }
    return accounts

# --- SIGN ---
def _execute_sign(api: GsAPI|SrAPI|ZzzAPI):
    info = api.get_sign_info()

    if info['retcode'] != 0:
        return f'"ERROR": {info}'

    if info['data']['is_sign']:
        return f'"Already sign-in": {info}'

    response = api.sign()
    return response

def _sign_with_thread(name, api_dict: dict):
    results = {}

    with ThreadPoolExecutor(max_workers=3) as pool:
        future_to_game = {pool.submit(_execute_sign, api): game for game, api in api_dict.items()}
        for fut in future_to_game:
            game = future_to_game[fut]
            results[game] = fut.result()

    print(f"# {name}")
    for game in ["gs", "sr", "zzz"]:
        if game in results:
            print(f"[{game}]")
            print(results[game])

def run_all_sign(accounts:dict):
    print('-'*6 + ' CHECK-IN ' + '-'*6)
    
    with ThreadPoolExecutor(max_workers=len(accounts)) as pool:
        for name, api_dict in accounts.items():
            pool.submit(_sign_with_thread, name, api_dict)

# --- CDKeys ---
def _fetch_cdkeys(api: GsAPI|SrAPI|ZzzAPI):
    data = api.fetch_channel_materials()
    if data['retcode'] != 0:
        raise RuntimeError(f'[ERROR] [/materials]: {data}')
    
    codes = []
    for module in data.get('data', {}).get('modules', []):
        exchange_group = module.get('exchange_group')
        if not exchange_group:
            continue

        for bonus_info in exchange_group.get('bonuses', []):
            code = bonus_info.get('exchange_code')
            if code:
                codes.append(code)
    return codes

def fetch_all_cdkeys(api_dict: dict):
    print('-'*6 + ' CDKEYS ' + '-'*6)

    with ThreadPoolExecutor(max_workers=len(api_dict)) as ex:
        futures = {game: ex.submit(_fetch_cdkeys, api) for game, api in api_dict.items()}
        cdkeys = {game: fut.result() for game, fut in futures.items()}

    cdkeys = {game: codes for game, codes in cdkeys.items() if codes}

    if not any(cdkeys.values()):
        raise LookupError("All CDKey lists are \"empty\". Exit now.")

    return cdkeys

# --- UID ---
def _fetch_uid(api: GsAPI|SrAPI|ZzzAPI):
    data = api.get_user_game_roles_by_ltoken()

    if data['retcode'] != 0:
        raise LookupError(f'[ERROR] [/getUserGameRolesByLtoken]: {data}')

    items = data.get("data", {}).get("list", [])
    if not items or not items[0].get("game_uid"):
        return None
    
    item = items[0]
    return {
        "game_uid": item.get("game_uid"),
        "game_biz": item.get("game_biz"),
        "region": item.get("region")
    }

def fetch_all_uid(accounts: dict, target_name:tuple):
    uid_data = {}

    for name, api_dict in accounts.items():
        with ThreadPoolExecutor(max_workers=len(api_dict)) as pool:
            futures = {
                game: pool.submit(_fetch_uid, api)
                for game, api in api_dict.items() if game in target_name
            }
            uid_data[name] = {
                game: (uid_info, api_dict[game])
                for game, fut in futures.items()
                if (uid_info:=fut.result())
            }
    return uid_data

# --- REDEEM CODE ---
def _redeem_code(api, cdkeys, uid_info, account, game):
    output = []
    output.append(f"# {account}")  # dòng này sẽ bị loại khi gộp log
    #output.append(f"[{game}] UID: {uid_info['game_uid']} ({uid_info['region']})")
    output.append(f"[{game}]")
    for idx, key in enumerate(cdkeys):
        response = api.exchange_cdkey(uid_info, key)
        output.append(f"{key}: {response}")
        if idx != len(cdkeys) - 1:
            time.sleep(5)  # sleep giữa các code, skip with last key
    return account, game, "\n".join(output)

def run_all_redeem_code(all_uid: dict, cdkeys: dict):
    max_workers_limit = 32
    tasks = []

    for account, game_dict in all_uid.items():
        for game in ["gs", "sr", "zzz"]:
            if game not in game_dict or not game_dict[game][0] or game not in cdkeys:
                continue
            uid_info, api = game_dict[game]
            all_code = cdkeys[game]
            tasks.append((api, all_code, uid_info, account, game))

    max_workers = min(len(tasks), max_workers_limit) if tasks else 1
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_task = {
            pool.submit(_redeem_code, api, all_code, uid_info, account, game): (account, game)
            for api, all_code, uid_info, account, game in tasks
        }

        for fut in future_to_task:
            account, game, log = fut.result()
            if account not in results:
                results[account] = {}
            results[account][game] = log

    for account in results:
        print(f"# {account}")
        for game in ["gs", "sr", "zzz"]:
            if game in results[account]:
                log_lines = results[account][game].splitlines() # remove message account
                for line in log_lines[1:]:
                    print(line)

