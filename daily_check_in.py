from helper import get_all_cookies_env, cookies_to_dict
from flows.gs_flow import GsFlow
from flows.sr_flow import SrFlow
from flows.zzz_flow import ZzzFlow
from concurrent.futures import ThreadPoolExecutor
import threading
import traceback

lock = threading.Lock()  # Để print không lộn xộn

def log(msg: str):
    """Print đồng bộ với lock."""
    with lock:
        print(msg)

def process_account(name, value):
    try:
        c = cookies_to_dict(value)
        gs = GsFlow(c)
        sr = SrFlow(c)
        zzz = ZzzFlow(c)

        prologue = f'------ {name} ------'
        log(prologue)

        log('[Genshin] Process check-in:')
        gs.process_checkin()

        log('[Star Rail] Process check-in:')
        sr.process_checkin()

        log('[ZZZ] Process check-in:')
        zzz.process_checkin()

        log(f'{len(prologue)*"-"}\n')

    except Exception as e:
        # In lỗi đầy đủ và gọn với traceback
        log(f'Error processing {name}: {e}\n{traceback.format_exc()}')

def process_all_checkin():
    cookie_accounts = get_all_cookies_env()

    if not cookie_accounts:
        log('No cookies env found.')
        return

    # Sử dụng ThreadPoolExecutor để giới hạn số thread đồng thời
    max_workers = min(5, len(cookie_accounts))  # tối đa 5 thread
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for name, value in cookie_accounts.items():
            executor.submit(process_account, name, value)

if __name__ == "__main__":
    process_all_checkin()
