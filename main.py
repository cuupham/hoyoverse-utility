from core.utils import get_cookies_env
from controllers.api_controller import initialize_api, get_api_0
from controllers.sign_controller import multi_sign_in
from controllers.redeem_controller import fetch_all_cdkeys, run_redeem_all

from traceback import format_exc


def main():
    if not (raw_cookies := get_cookies_env()):
        print('Cookies environment is "empty". Exit now')
        return

    apis = initialize_api(raw_cookies)
    
    # Sign-in
    multi_sign_in(apis)

    # Redeem
    try:
        api_0 = get_api_0(apis)
        all_cdkeys = fetch_all_cdkeys(api_0)
        run_redeem_all(apis, all_cdkeys)
    except LookupError as e:
        print(e)
        return
    except Exception:
        
        print(format_exc())


if __name__ == '__main__':
    main()