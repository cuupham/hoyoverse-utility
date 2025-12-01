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

    prologue = f"------ {cookie_name} ------"
    epilogue = "-" * len(prologue)
    message = (
        f"{prologue}\n"
        f"• Genshin:\n   → {gs_result}\n"
        f"• Star Rail:\n   → {sr_result}\n"
        f"• ZZZ:\n   → {zzz_result}\n"
        f"{epilogue}\n"
    )

    print(message)

def main():
    all_cookies = cookies_env()

    if not all_cookies:
        print("[ERROR]: No cookies found. Exiting ...")
        return

    for cookie_name, cookies_value in all_cookies.items():
        threading.Thread(target=process_all_checkin, args=(cookie_name, cookies_value,)).start()
        

if __name__ == "__main__":
    main()