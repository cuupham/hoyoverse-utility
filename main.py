
from src.controller.cookies_controller import CookiesController as cc
from src.controller.sign_controller import SignController as sc
from src.controller.redeem_controller import RedeemController as rc

from concurrent.futures import ThreadPoolExecutor, as_completed
from traceback import format_exc


def check_in_task(user_cookies):
    try:
        return sc.run_multi_sign(user_cookies)
    except Exception as e:
        return f'[Check-in] failed: {e}'

def redeem_task(user_cookies):
    try:
        first_cookies_value = next(iter(user_cookies.values()))
        multi_cdkeys = rc.fetch_multi_cdkeys(first_cookies_value)
        multi_uid = rc.fetch_multi_uid(user_cookies)
        results = rc.redeem_multi_code(user_cookies, multi_cdkeys, multi_uid)
        return results
    except Exception as e:
        return f'[Redeem] failed: {e}'

def _show_log(name, result):
    print(name.upper().center(80, '≡'))
    if name == 'checkin':
        if isinstance(result, dict):
            for acc_name, games_dict in result.items():
                print(acc_name.center(80, '-'))
                for game_name, r in games_dict.items():
                    print(f'{game_name:10}: {r}')
        else:
            print(result)

    elif name == 'redeem':
        if isinstance(result, dict):
            for acc_name, results_dict in result.items():
                print(acc_name.center(80, '┅'))
                for (game_code, server), code_list in results_dict.items():
                    print(f'◀ [{game_code}][{server}] ▶')
                    for cdkey, response in code_list:
                        print(f"{cdkey:<18}: {response['message']}; retcode={response['retcode']}")
        else:
            print(result)

def main():
    try:
        env_cookies = cc.require_env_cookies()
        user_cookies = cc.collect_valid_env_cookies(env_cookies)
        
        # Main Flow
        tasks = {
            'checkin': check_in_task,
            'redeem': redeem_task
        }

        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = { executor.submit(func, user_cookies): name for name, func in tasks.items() }

            for future in as_completed(futures):
                name = futures[future]
                result = future.result()
                _show_log(name, result)
    except (ValueError, RuntimeError) as e:
        print(e)
        return
    except Exception:
        print(format_exc())

if __name__ == '__main__':
    main()