import asyncio
from helper import get_all_cookies_env, cookies_to_dict
from flows.gs_flow import GsFlow
from flows.sr_flow import SrFlow
from flows.zzz_flow import ZzzFlow


async def process_account(cookie_name, cookie_values):
    cookie_dict = cookies_to_dict(cookie_values)
    gs_flow = GsFlow(cookie_dict)
    sr_flow = SrFlow(cookie_dict)
    zzz_flow = ZzzFlow(cookie_dict)

    prologue = f"----- {cookie_name} -----"
    print(prologue)

    loop = asyncio.get_running_loop()

    for name, flow in [("Genshin", gs_flow), ("Star Rail", sr_flow), ("ZZZ", zzz_flow)]:
        print(f"[{name}] Process check-in:")
        try:
            # Chạy process_checkin đồng bộ trong executor
            await loop.run_in_executor(None, flow.process_checkin)
        except Exception as e:
            print(f"[{name}] Error: {e}")

    print('-' * len(prologue) + '\n')


async def main():
    cookies_list = get_all_cookies_env()

    if not cookies_list:
        print("No cookies found in environment. Exiting...")
        return

    tasks = [process_account(name, values) for name, values in cookies_list.items()]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
