"""Main entry point - HoYoLab Auto Check-in & Redeem Code Tool"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from typing import TYPE_CHECKING

from src.api.client import create_session
from src.api.checkin import check_cookie, run_checkin_for_account
from src.api.redeem_fetch import fetch_all_cdkeys, fetch_all_uids
from src.api.redeem_exchange import run_redeem_for_account
from src.config import HEADER_WIDTH, SYSTEM_MESSAGES
from src.models.account import Account
from src.models.game import Game
from src.utils.display import display_checkin, display_redeem, display_redeem_results
from src.utils.helpers import TZ, get_accounts_from_env
from src.utils.logger import ctx, log_error, log_print

if TYPE_CHECKING:
    import aiohttp


def print_header() -> None:
    """In header của tool."""
    log_print("=" * HEADER_WIDTH)
    log_print("HOYOLAB AUTO TOOL")
    log_print(f"Time: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    log_print(f"Trace: {ctx.trace_id}")
    log_print("=" * HEADER_WIDTH)


async def validate_accounts(
    session: aiohttp.ClientSession,
    accounts: list[Account],
) -> list[Account]:
    """Validate tất cả cookies song song."""
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

    log_print(f"Tổng: {len(valid_accounts)}/{len(accounts)} accounts hợp lệ")
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


async def fetch_app_data(
    session: aiohttp.ClientSession,
    accounts: list[Account],
) -> tuple[dict[Game, list[str]], dict[str, dict[Game, dict[str, str]]]]:
    """Fetch dữ liệu nền (CDKeys và UIDs) cho tất cả accounts."""
    if not accounts:
        return {game: [] for game in Game}, {}

    # Fetch CDKeys và UIDs song song
    # CDKeys: thử từng account cho đến khi có kết quả (fallback)
    cdkeys_tasks = [fetch_all_cdkeys(session, acc) for acc in accounts]
    uids_tasks = [fetch_all_uids(session, acc) for acc in accounts]

    all_cdkeys_results, uids_results = await asyncio.gather(
        asyncio.gather(*cdkeys_tasks),
        asyncio.gather(*uids_tasks),
    )

    # Chọn kết quả CDKeys tốt nhất (account có nhiều codes nhất)
    cdkeys: dict[Game, list[str]] = {game: [] for game in Game}
    for result in all_cdkeys_results:
        if sum(len(codes) for codes in result.values()) > sum(len(codes) for codes in cdkeys.values()):
            cdkeys = result

    account_uids = {acc.name: uids for acc, uids in zip(accounts, uids_results)}
    return cdkeys, account_uids


async def run_redeem_for_all(
    session: aiohttp.ClientSession,
    accounts: list[Account],
    cdkeys: dict[Game, list[str]],
    account_uids: dict[str, dict[Game, dict[str, str]]],
) -> dict[str, dict]:
    """Thực thi redeem cho các accounts có UID."""
    eligible = [
        acc for acc in accounts
        if any(account_uids[acc.name].get(game) for game in Game)
    ]

    if not eligible:
        return {}

    results = await asyncio.gather(
        *(run_redeem_for_account(session, acc, cdkeys, account_uids[acc.name]) for acc in eligible)
    )
    return {acc.name: res for acc, res in zip(eligible, results)}


async def main():
    """Main flow"""
    ctx.reset_timer()
    print_header()

    # Bước 1: Đọc accounts từ env
    env_accounts = get_accounts_from_env()
    if not env_accounts:
        log_error("SYSTEM", SYSTEM_MESSAGES["VALIDATION_NONE_FOUND"])
        sys.exit(1)

    accounts: list[Account] = []
    for name, cookie_str in sorted(env_accounts.items()):
        try:
            accounts.append(Account.from_env(name, cookie_str))
        except ValueError as e:
            log_error(name, str(e))

    if not accounts:
        log_error("SYSTEM", SYSTEM_MESSAGES["VALIDATION_NONE_VALID"])
        sys.exit(1)

    async with create_session() as session:
        # Bước 2: Validate cookies
        valid_accounts = await validate_accounts(session, accounts)
        if not valid_accounts:
            log_error("SYSTEM", SYSTEM_MESSAGES["VALIDATION_ALL_FAILED"])
            sys.exit(1)

        # Bước 3: Check-in + Fetch data song song
        checkin_results, (cdkeys, account_uids) = await asyncio.gather(
            run_checkin(session, valid_accounts),
            fetch_app_data(session, valid_accounts),
        )

        # Hiển thị checkin ngay (không đợi redeem)
        display_checkin(checkin_results)

        # Bước 4: Redeem (dựa trên dữ liệu đã fetch)
        display_redeem(cdkeys, account_uids)

        total_codes = sum(len(codes) for codes in cdkeys.values())
        if total_codes > 0:
            redeem_results = await run_redeem_for_all(session, valid_accounts, cdkeys, account_uids)
            if redeem_results:
                display_redeem_results(redeem_results)
            else:
                log_print(SYSTEM_MESSAGES["REDEEM_NO_UIDS"])

    log_print("=" * HEADER_WIDTH)
    log_print(f"DONE - {ctx.elapsed_seconds:.1f}s")
    log_print("=" * HEADER_WIDTH)


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
