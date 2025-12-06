from helper import parse_cookies, cookies_env
from flows.gs_flow import GsFlow
from flows.sr_flow import SrFlow
from flows.zzz_flow  import ZzzFlow

import threading


def process_checkin(c_name: str, c_value: str):
    cookies_dict  = parse_cookies(c_value)
    gs  = GsFlow(cookies_dict)
    sr  = SrFlow(cookies_dict)
    zzz = ZzzFlow(cookies_dict)

    gs_result = gs.process_checkin()
    sr_result = sr.process_checkin()
    zzz_result = zzz.process_checkin()

    message = (
        f"------ {c_name} ------\n"
        f"[Genshin]:\n• {gs_result}\n"
        f"[Star Rail]:\n• {sr_result}\n"
        f"[ZZZ]:\n• {zzz_result}\n\n"
    )
    print(message)

def main():
    cookies_raw = cookies_env()

    if not cookies_raw:
        print("[ERROR] COOKIES env not found. Exiting.")
        return

    for k, v in cookies_raw.items():
        if v:
            threading.Thread(target=process_checkin, args=(k, v)).start()
        

if __name__ == "__main__":
    main()



    