"""Main entry point - HoYoLab Auto Check-in & Redeem Code Tool"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from typing import TYPE_CHECKING

from src.api.client import create_session
from src.api.checkin import check_cookie, run_checkin_for_account
from src.api.redeem import fetch_all_cdkeys, fetch_all_uids, run_redeem_for_account
from src.config import HEADER_WIDTH, SYSTEM_MESSAGES
from src.models.account import Account
from src.models.game import Game
from src.utils.helpers import get_accounts_from_env
from src.utils.logger import ctx, log_error, log_info, log_print

if TYPE_CHECKING:
    import aiohttp


def print_header() -> None:
    """In header của tool."""
    log_print("=" * HEADER_WIDTH)
    log_print("HOYOLAB AUTO TOOL")
    log_print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_print(f"Trace: {ctx.trace_id}")
    log_print("=" * HEADER_WIDTH)


def print_section(title: str) -> None:
    """In section header."""
    log_print(f"--- {title} ---")
    log_print()


def _format_checkin_line(game: Game, result: dict) -> str:
    """Format một dòng kết quả check-in."""
    status = "✓" if result["success"] else "✗"
    game_name = game.value.name
    if result["success"]:
        if SYSTEM_MESSAGES["CHECKIN_ALREADY"] in result["message"]:
            return f"  {game_name}: {status} {SYSTEM_MESSAGES['CHECKIN_ALREADY']}"
        return f"  {game_name}: {status} {result['message']} (Ngày {result['day']})"
    return f"  {game_name}: ✗ {result['message']}"


async def validate_accounts(
    session: aiohttp.ClientSession,
    accounts: list[Account],
) -> list[Account]:
    """Validate tất cả cookies song song

    Returns:
        List các accounts hợp lệ
    """
    log_print("--- KIỂM TRA ACCOUNTS ---")

    tasks = [check_cookie(session, acc) for acc in accounts]
    results = await asyncio.gather(*tasks)

    valid_accounts = []

    for acc, result in zip(accounts, results):
        if result["valid"]:
            log_print(f"[✓] {acc.name}: {SYSTEM_MESSAGES['VALIDATION_VALID']} ({result['email_mask']})")
            valid_accounts.append(acc)
        else:
            log_print(f"[✗] {acc.name}: {result['error']}")

    log_print(f"\nTổng: {len(valid_accounts)}/{len(accounts)} accounts hợp lệ")
    log_print()

    return valid_accounts


async def run_checkin(
    session: aiohttp.ClientSession,
    accounts: list[Account],
) -> dict[str, dict]:
    """Chạy check-in cho tất cả accounts song song."""
    tasks = [run_checkin_for_account(session, acc) for acc in accounts]
    results = await asyncio.gather(*tasks)
    return {acc.name: res for acc, res in zip(accounts, results)}


def display_checkin(all_results: dict[str, dict]) -> None:
    """Hiển thị kết quả check-in."""
    print_section("CHECK-IN")
    for acc_name, results in all_results.items():
        log_print(f"=== {acc_name} ===")
        for game, result in results.items():
            log_print(_format_checkin_line(game, result))
        log_print()


def _display_cdkeys(cdkeys: dict[Game, list[str]]) -> None:
    """Hiển thị danh sách CDKeys đã fetch."""
    log_print(">> Fetching CDKeys...")
    for game, codes in cdkeys.items():
        if codes:
            log_print(f"[SYSTEM] {game.value.name}: {len(codes)} {SYSTEM_MESSAGES['SYSTEM_CODES_FOUND']} {codes}")
        else:
            log_print(f"[SYSTEM] {game.value.name}: {SYSTEM_MESSAGES['SYSTEM_NO_CODES']}")
    log_print()


def _display_uids(account_uids: dict[str, dict[Game, dict[str, str]]]) -> None:
    """Hiển thị danh sách UIDs tìm thấy."""
    log_print(">> Fetching UIDs...")
    for acc_name, uids in account_uids.items():
        uid_info = []
        for game in Game:
            game_uids = uids.get(game, {})
            if game_uids:
                regions = ", ".join(game_uids.keys())
                uid_info.append(f"{game.value.name}({regions})")

        if uid_info:
            log_print(f"  {acc_name}: {', '.join(uid_info)}")
        else:
            log_print(f"  {acc_name}: {SYSTEM_MESSAGES['SYSTEM_NO_UIDS']}")
    log_print()


def _display_redeem_results(account_uids: dict, results_map: dict) -> None:
    """Hiển thị kết quả redeem chi tiết từng account."""
    for acc_name, game_results in results_map.items():
        if not game_results:
            continue
        log_print(f"=== {acc_name} ===")

        for game, regions in game_results.items():
            log_print(f"  {game.value.name}:")
            for region, codes_res in regions.items():
                log_print(f"    {region}:")
                for code, res in codes_res.items():
                    status = "✓" if res["success"] else "✗"
                    if res.get("skipped"):
                        log_print(f"      {code}: {res['message']}")
                    else:
                        log_print(f"      {code}: {status} {res['message']}")
        log_print()


async def fetch_app_data(
    session: aiohttp.ClientSession,
    accounts: list[Account],
) -> tuple[dict[Game, list[str]], dict[str, dict[Game, dict[str, str]]]]:
    """Fetch dữ liệu nền (CDKeys và UIDs) cho tất cả accounts."""
    # Fetch CDKeys (dùng account đầu tiên làm đại diện fetch public data)
    cdkeys_task = fetch_all_cdkeys(session, accounts[0])

    # Fetch UIDs cho tất cả accounts song song
    uids_tasks = [fetch_all_uids(session, acc) for acc in accounts]

    cdkeys, uids_results = await asyncio.gather(cdkeys_task, asyncio.gather(*uids_tasks))

    account_uids = {acc.name: uids for acc, uids in zip(accounts, uids_results)}
    return cdkeys, account_uids


async def run_redeem_for_all(
    session: aiohttp.ClientSession,
    accounts: list[Account],
    cdkeys: dict[Game, list[str]],
    account_uids: dict[str, dict[Game, dict[str, str]]],
) -> dict[str, dict]:
    """Thực thi redeem cho các accounts có UID."""
    tasks = []
    task_accounts = []

    for acc in accounts:
        # Chỉ chạy redeem nếu account có ít nhất 1 UID cho bất kỳ game nào
        if any(account_uids[acc.name].get(game) for game in Game):
            tasks.append(run_redeem_for_account(session, acc, cdkeys, account_uids[acc.name]))
            task_accounts.append(acc.name)

    redeem_results = await asyncio.gather(*tasks)
    return {name: res for name, res in zip(task_accounts, redeem_results)}


def display_redeem(
    cdkeys: dict,
    account_uids: dict,
    results_map: dict,
) -> None:
    """Hiển thị toàn bộ kết quả redeem."""
    print_section("REDEEM CODE")

    _display_cdkeys(cdkeys)

    total_codes = sum(len(codes) for codes in cdkeys.values())
    if total_codes == 0:
        log_info("SYSTEM", SYSTEM_MESSAGES["REDEEM_NO_CODES"])
        return

    _display_uids(account_uids)

    if not results_map:
        log_error("SYSTEM", SYSTEM_MESSAGES["REDEEM_NO_UIDS"])
        return

    _display_redeem_results(account_uids, results_map)


async def main():
    """Main flow"""
    print_header()

    # Bước 1: Đọc accounts từ env
    env_accounts = get_accounts_from_env()

    if not env_accounts:
        log_error("SYSTEM", SYSTEM_MESSAGES["VALIDATION_NONE_FOUND"])
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
        log_error("SYSTEM", SYSTEM_MESSAGES["VALIDATION_NONE_VALID"])
        sys.exit(1)

    # Tạo session
    async with create_session() as session:
        # Bước 2: Validate cookies (giữ nguyên vì nó in ra ngay lúc đầu để check)
        valid_accounts = await validate_accounts(session, accounts)

        if not valid_accounts:
            log_error("SYSTEM", SYSTEM_MESSAGES["VALIDATION_ALL_FAILED"])
            sys.exit(1)

        # Bước 3: Chạy tất cả mọi thứ song song (không log)
        # 3.1. Chạy Check-in
        checkin_task = run_checkin(session, valid_accounts)

        # 3.2. Fetch dữ liệu nền cho Redeem (CDKeys & UIDs)
        app_data_task = fetch_app_data(session, valid_accounts)

        checkin_results, (cdkeys, account_uids) = await asyncio.gather(checkin_task, app_data_task)

        # 3.3. Chạy Redeem (dựa trên dữ liệu đã fetch)
        redeem_results = await run_redeem_for_all(session, valid_accounts, cdkeys, account_uids)

        # Bước 4: Hiển thị kết quả theo thứ tự
        display_checkin(checkin_results)
        display_redeem(cdkeys, account_uids, redeem_results)

    # Bước 5: Kết thúc
    log_print("=" * HEADER_WIDTH)
    log_print(f"DONE - {ctx.elapsed_seconds:.1f}s")
    log_print("=" * HEADER_WIDTH)


if __name__ == "__main__":
    asyncio.run(main())
