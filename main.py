from core.utils import get_cookies_env
from core.controller import run_all_sign, get_accounts, fetch_all_cdkeys, fetch_all_uid, run_all_redeem_code
from traceback import format_exc


def main():
    if not (cookies_raw := get_cookies_env()):
        raise RuntimeError('Cookies Env is empty. The program will exit.')

    accounts = get_accounts(cookies_raw)
    
    # Check-in
    run_all_sign(accounts)

    # Redeem
    try: 
        cdkeys = fetch_all_cdkeys(next(iter(accounts.values())))
        all_uid = fetch_all_uid(accounts, tuple(cdkeys.values()))
        run_all_redeem_code(all_uid, cdkeys)
    except LookupError as e:
        print(e)
        return
    except Exception:
        print(format_exc())

if __name__ == '__main__':
    main()
