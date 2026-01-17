"""Main entry point - HoYoLab Auto Check-in & Redeem Code Tool"""
import asyncio
import sys

from src.models.account import Account
from src.models.game import Game
from src.api.client import create_session
from src.api.checkin import check_cookie, run_checkin_for_account
from src.api.redeem import fetch_all_cdkeys, fetch_all_uids, run_redeem_for_account
from src.utils.helpers import get_accounts_from_env
from src.utils.logger import ctx, log_info, log_error


def print_header():
    """In header của tool"""
    from datetime import datetime
    print("=" * 60)
    print("                    HOYOLAB AUTO TOOL")
    print(f"                    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"                    Trace ID: {ctx.trace_id}")
    print("=" * 60)
    print()


def print_section(title: str):
    """In section header"""
    print("=" * 60)
    print(f"--- {title} ---")
    print("=" * 60)
    print()


async def validate_accounts(session, accounts: list[Account]) -> list[Account]:
    """Validate tất cả cookies song song
    
    Returns:
        List các accounts hợp lệ
    """
    print("--- KIỂM TRA ACCOUNTS ---")
    
    tasks = [check_cookie(session, acc) for acc in accounts]
    results = await asyncio.gather(*tasks)
    
    valid_accounts = []
    
    for acc, result in zip(accounts, results):
        if result["valid"]:
            print(f"[✓] {acc.name}: Hợp lệ ({result['email_mask']})")
            valid_accounts.append(acc)
        else:
            print(f"[✗] {acc.name}: {result['error']}")
    
    print(f"\nTổng: {len(valid_accounts)}/{len(accounts)} accounts hợp lệ")
    print()
    
    return valid_accounts


async def run_checkin(session, accounts: list[Account]):
    """Chạy check-in cho tất cả accounts"""
    print_section("CHECK-IN")
    
    for acc in accounts:
        print(f"=== {acc.name} ===")
        await run_checkin_for_account(session, acc)
        print()


async def run_redeem(session, accounts: list[Account]):
    """Chạy redeem cho tất cả accounts"""
    print_section("REDEEM CODE")
    
    # Fetch CDKeys sử dụng account đầu tiên
    print(">> Fetching CDKeys...")
    cdkeys = await fetch_all_cdkeys(session, accounts[0])
    print()
    
    # Kiểm tra có codes không
    total_codes = sum(len(codes) for codes in cdkeys.values())
    if total_codes == 0:
        log_info("SYSTEM", "Không có codes nào để redeem")
        return
    
    # Fetch UIDs cho tất cả accounts
    print(">> Fetching UIDs...")
    account_uids = {}
    
    for acc in accounts:
        uids = await fetch_all_uids(session, acc)
        account_uids[acc.name] = uids
        
        # Format output
        uid_info = []
        for game in Game:
            game_uids = uids.get(game, {})
            if game_uids:
                regions = ", ".join(game_uids.keys())
                uid_info.append(f"{game.value.name}({regions})")
        
        if uid_info:
            print(f"  {acc.name}: {', '.join(uid_info)}")
        else:
            print(f"  {acc.name}: Không có UID nào")
    
    print()
    
    # Kiểm tra có accounts nào có UID không
    accounts_with_uids = [
        acc for acc in accounts 
        if any(account_uids[acc.name].get(game) for game in Game)
    ]
    
    if not accounts_with_uids:
        log_error("SYSTEM", "Tất cả accounts đều không có UID - không thể redeem!")
        return
    
    # Redeem cho từng account
    for acc in accounts_with_uids:
        print(f"=== {acc.name} ===")
        uids = account_uids[acc.name]
        
        # In game/region info trước
        for game in Game:
            game_uids = uids.get(game, {})
            codes = cdkeys.get(game, [])
            
            if not codes or not game_uids:
                continue
            
            print(f"  {game.value.name}:")
            for region, uid in game_uids.items():
                print(f"    {region}:")
                # Redeem codes sẽ được log bởi run_redeem_for_account
        
        await run_redeem_for_account(session, acc, cdkeys, uids)
        print()


async def main():
    """Main flow"""
    print_header()
    
    # Bước 1: Đọc accounts từ env
    env_accounts = get_accounts_from_env()
    
    if not env_accounts:
        log_error("SYSTEM", "Không tìm thấy account nào trong environment variables!")
        log_error("SYSTEM", "Hãy đảm bảo có ít nhất 1 biến ACC_* với cookie string.")
        sys.exit(1)
    
    # Parse accounts
    accounts: list[Account] = []
    for name, cookie_str in sorted(env_accounts.items()):
        try:
            acc = Account.from_env(name, cookie_str)
            accounts.append(acc)
        except ValueError as e:
            log_error(name, str(e))
    
    if not accounts:
        log_error("SYSTEM", "Không có account nào hợp lệ để tiếp tục!")
        sys.exit(1)
    
    # Tạo session
    async with create_session() as session:
        # Bước 2: Validate cookies
        valid_accounts = await validate_accounts(session, accounts)
        
        if not valid_accounts:
            log_error("SYSTEM", "Tất cả cookies đều không hợp lệ!")
            sys.exit(1)
        
        # Bước 3: Check-in và Redeem song song
        await run_checkin(session, valid_accounts)
        await run_redeem(session, valid_accounts)
    
    # Bước 4: Kết thúc
    print("=" * 60)
    print("--- KẾT THÚC ---")
    print(f"Thời gian chạy: {ctx.elapsed_seconds:.1f} giây")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
