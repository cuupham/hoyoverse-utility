from helper import parse_cookies, cookies_env
from flows.gs_flow import GsFlow
from flows.sr_flow import SrFlow
from flows.zzz_flow  import ZzzFlow
import threading


def process_all_checkin(cookie_name: str, cookies_value: str):
    
    parsed_cookies  = parse_cookies(cookies_value)
    gs = GsFlow(parsed_cookies)
    sr = SrFlow(parsed_cookies)
    zzz = ZzzFlow(parsed_cookies)

    gs_result = gs.process_checkin()
    sr_result = sr.process_checkin()
    zzz_result = zzz.process_checkin()

    prologue = f'------ {cookie_name} ------'
    message = f'{prologue}\n[Genshin]:\n\t{gs_result}\n[Star Rail]:\n\t{sr_result}\n[ZZZ]:\n\t{zzz_result}\n{'-'*len(prologue)}'
    print(message)

def main():
    all_cookies = cookies_env()

    if not all_cookies:
        print("[ERROR]: No cookies found. Exiting ...")
        return

    for cookie_name, cookies_value in all_cookies.items():
        threading.Thread(target=process_all_checkin, args=(cookie_name, cookies_value,)).start()
        #process_all_checkin(cookie_name, cookies_value)
        

if __name__ == "__main__":
    main()