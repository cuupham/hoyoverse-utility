"""Main entry point - HoYoLab Auto Check-in & Redeem Code Tool"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from typing import TYPE_CHECKING

from src.api.checkin import check_cookie, run_checkin_for_account
from src.api.client import create_session
from src.api.redeem_exchange import run_redeem_for_account
from src.api.redeem_fetch import fetch_all_uids, fetch_cdkeys
from src.config import HEADER_WIDTH, SYSTEM_MESSAGES
from src.models.account import Account
from src.models.game import Game
from src.models.results import (
    AccountValidationResult,
    CheckinResults,
    ProviderResult,
    RedemptionData,
    RedemptionResults,
)
from src.utils.display import display_checkin, display_redeem, display_redeem_results
from src.utils.environment import get_accounts_from_env
from src.utils.logger import ctx, log_error, log_print
from src.utils.timekeeping import TZ

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
) -> AccountValidationResult:
    """Validate tất cả cookies song song."""
    log_print(SYSTEM_MESSAGES["SECTION_ACCOUNTS"])

    tasks = [check_cookie(session, acc) for acc in accounts]
    results = await asyncio.gather(*tasks)

    valid_accounts = []
    errors = []
    for acc, result in zip(accounts, results):
        if result["valid"]:
            log_print(
                f"[✓] {acc.name}: {SYSTEM_MESSAGES['VALIDATION_VALID']} ({result['email_mask']})"
            )
            valid_accounts.append(acc)
        else:
            error = f"{acc.name}: {result['error']}"
            errors.append(error)
            log_print(f"[✗] {error}")

    log_print(
        SYSTEM_MESSAGES["VALIDATION_SUMMARY"].format(
            valid=len(valid_accounts), total=len(accounts)
        )
    )
    log_print()
    return AccountValidationResult(valid_accounts, errors)


async def run_checkin(
    session: aiohttp.ClientSession,
    accounts: list[Account],
) -> CheckinResults:
    """Chạy check-in cho tất cả accounts song song."""
    tasks = [run_checkin_for_account(session, acc) for acc in accounts]
    results = await asyncio.gather(*tasks)
    return {acc.name: res for acc, res in zip(accounts, results)}


async def _fetch_cdkeys_with_fallback(
    session: aiohttp.ClientSession,
    accounts: list[Account],
) -> dict[Game, ProviderResult[list[str]]]:
    """Retry empty/failed games with another account, preserving other games."""

    async def fetch_game(game: Game) -> ProviderResult[list[str]]:
        empty_success = False
        result: ProviderResult[list[str]] = ProviderResult(
            [], error="No accounts available"
        )
        for account in accounts:
            result = await fetch_cdkeys(session, account, game)
            if result.success:
                if result.data:
                    return result
                empty_success = True
        return ProviderResult([], retcode=0) if empty_success else result

    results = await asyncio.gather(*(fetch_game(game) for game in Game))
    return dict(zip(Game, results))


async def fetch_redemption_data(
    session: aiohttp.ClientSession,
    accounts: list[Account],
) -> RedemptionData:
    """Fetch dữ liệu nền (CDKeys và UIDs) cho tất cả accounts."""
    if not accounts:
        return RedemptionData({game: [] for game in Game}, {})

    # CDKeys: per-game fallback; UID discovery remains account-wide.
    # UIDs: per-account → fetch song song
    # Hai nhóm chạy đồng thời để không mất parallelism.
    cdkeys, uids_results = await asyncio.gather(
        _fetch_cdkeys_with_fallback(session, accounts),
        asyncio.gather(*(fetch_all_uids(session, acc) for acc in accounts)),
    )

    errors = [
        f"CDKeys / {game.value.name}: {result.error}"
        for game, result in cdkeys.items()
        if not result.success
    ]
    account_uids = {}
    for account, result in zip(accounts, uids_results):
        if result.success:
            account_uids[account.name] = result.data
        else:
            errors.append(f"UIDs / {account.name}: {result.error}")
    return RedemptionData(
        {game: result.data for game, result in cdkeys.items() if result.success},
        account_uids,
        errors,
    )


async def run_redeem_for_all(
    session: aiohttp.ClientSession,
    accounts: list[Account],
    cdkeys: dict[Game, list[str]],
    account_uids: dict[str, dict[Game, dict[str, str]]],
) -> RedemptionResults:
    """Thực thi redeem cho các accounts có UID."""
    eligible = [
        acc
        for acc in accounts
        if any(
            cdkeys.get(game) and account_uids.get(acc.name, {}).get(game)
            for game in Game
        )
    ]

    if not eligible:
        return {}

    results = await asyncio.gather(
        *(
            run_redeem_for_account(session, acc, cdkeys, account_uids[acc.name])
            for acc in eligible
        )
    )
    return {acc.name: res for acc, res in zip(eligible, results)}


async def main() -> None:
    """Main flow"""
    ctx.reset_timer()
    print_header()

    # Bước 1: Đọc accounts từ env
    env_accounts = get_accounts_from_env()
    if not env_accounts:
        log_error("SYSTEM", SYSTEM_MESSAGES["VALIDATION_NONE_FOUND"])
        sys.exit(1)

    accounts: list[Account] = []
    failed_run = False
    for name, cookie_str in sorted(env_accounts.items()):
        try:
            accounts.append(Account.from_cookie_string(name, cookie_str))
        except ValueError as error:
            log_error(name, str(error))
            failed_run = True

    if not accounts:
        log_error("SYSTEM", SYSTEM_MESSAGES["VALIDATION_NONE_VALID"])
        sys.exit(1)

    async with create_session() as session:
        # Bước 2: Validate cookies
        validation = await validate_accounts(session, accounts)
        valid_accounts = validation.valid_accounts
        failed_run = failed_run or bool(validation.errors)
        if not valid_accounts:
            log_error("SYSTEM", SYSTEM_MESSAGES["VALIDATION_ALL_FAILED"])
            sys.exit(1)

        # Bước 3: Check-in + Fetch data song song
        checkin_results, redemption_data = await asyncio.gather(
            run_checkin(session, valid_accounts),
            fetch_redemption_data(session, valid_accounts),
        )

        # Hiển thị checkin ngay (không đợi redeem)
        display_checkin(checkin_results)

        # Bước 4: Redeem (dựa trên dữ liệu đã fetch)
        cdkeys, account_uids = redemption_data.cdkeys, redemption_data.account_uids
        display_redeem(cdkeys, account_uids, redemption_data.errors)
        failed_run = (
            failed_run
            or bool(redemption_data.errors)
            or any(
                not result["success"] and result.get("status") != "no_character"
                for results in checkin_results.values()
                for result in results.values()
            )
        )

        total_codes = sum(len(codes) for codes in cdkeys.values())
        if total_codes > 0:
            redeem_results = await run_redeem_for_all(
                session, valid_accounts, cdkeys, account_uids
            )
            if redeem_results:
                display_redeem_results(redeem_results)
                failed_run = failed_run or any(
                    not result["success"] and result.get("error_kind") != "provider"
                    for games in redeem_results.values()
                    for regions in games.values()
                    for codes in regions.values()
                    for result in codes.values()
                )
            else:
                log_error("SYSTEM", SYSTEM_MESSAGES["REDEEM_NO_UIDS"])
                failed_run = True

    log_print("=" * HEADER_WIDTH)
    log_print(f"DONE - {ctx.elapsed_seconds:.1f}s")
    log_print("=" * HEADER_WIDTH)
    if failed_run:
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
