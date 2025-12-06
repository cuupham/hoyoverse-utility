from helper import cookies_env
from helper import parse_cookies

from flows.gs_flow import GsFlow
from flows.sr_flow import SrFlow
from flows.zzz_flow import ZzzFlow

import threading


def process_redeem(c_name, c_value):
    cookies_dict = parse_cookies(c_value)

    gs  = GsFlow(cookies_dict)
    sr  = SrFlow(cookies_dict)
    zzz = ZzzFlow(cookies_dict)

    # Run
    sr_result = sr.claim_redeem_code()

    # print
    txt = (
        f"------ {c_name} ------\n"
        f"[Star Rail]:\n{sr_result}"
    )
    print(txt)

def main():
    cookies_raw = cookies_env()

    if not cookies_raw:
        print("[ERROR] COOKIES env not found. Exiting.")
        return
    
    print('==================== REDEEM CODE ====================')
    for k, v in cookies_raw.items():
        if v:
            threading.Thread(target=process_redeem, args=(k, v)).start()
    

if __name__ == '__main__':
    main()