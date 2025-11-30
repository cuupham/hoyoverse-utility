from helper import parse_cookies, cookies_env
from flows.gs_flow import GsFlow
from flows.sr_flow import SrFlow
from flows.zzz_flow  import ZzzFlow


def process_all_checkin(cookies_value: str):
    parsed_cookies  = parse_cookies(cookies_value)
    gs = GsFlow(parsed_cookies)
    sr = SrFlow(parsed_cookies)
    zzz = ZzzFlow(parsed_cookies)

    print('[Genshin]:')
    gs.process_checkin()

    print('[Star Rail]:')
    sr.process_checkin()

    print('[ZZZ]:')
    zzz.process_checkin()

def main():
    all_cookies = cookies_env()

    if not all_cookies:
        print("[ERROR] No cookies found")
        return

    for cookie_name, cookies_value in all_cookies:
        prologue = f'------ {cookie_name} ------'
        print(prologue)
        process_all_checkin(cookies_value)
        print('-' * len(prologue) + '\n')

if __name__ == "__main__":
    main()