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
from src.config import STATUS_ERROR, SYSTEM_MESSAGES
from src.models.account import Account
from src.models.game import Game
from src.models.results import (
    AccountValidationResult,
    CheckinResult,
    CheckinResults,
    ProviderResult,
    RedeemResult,
    RedemptionData,
    RedemptionResults,
)
from src.utils.display import (
    INDENT,
    display_checkin,
    display_failures,
    display_redeem,
    display_redeem_results,
    display_result,
)
from src.utils.environment import get_accounts_from_env
from src.utils.logger import ctx, log_error, log_print
from src.utils.summary import write_job_summary
from src.utils.timekeeping import TZ

if TYPE_CHECKING:
    import aiohttp


def print_header() -> None:
    """In header của tool."""
    log_print(
        SYSTEM_MESSAGES["HEADER"].format(
            time=datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"), trace=ctx.trace_id
        )
    )
    log_print()


async def validate_accounts(
    session: aiohttp.ClientSession,
    accounts: list[Account],
) -> AccountValidationResult:
    """Validate tất cả cookies song song."""
    tasks = [check_cookie(session, acc) for acc in accounts]
    results = await asyncio.gather(*tasks)

    valid_accounts = []
    errors = []
    name_w = max(len(acc.name) for acc in accounts) + 2
    lines = []
    for acc, result in zip(accounts, results):
        if result["valid"]:
            valid_accounts.append(acc)
            detail = result["email_mask"]
        else:
            errors.append(f"{acc.name} · {result['error']}")
            detail = STATUS_ERROR
        lines.append(f"{INDENT}{acc.name:<{name_w}}{detail}")

    log_print(
        SYSTEM_MESSAGES["SECTION_ACCOUNTS"].format(
            valid=len(valid_accounts), total=len(accounts)
        )
    )
    for line in lines:
        log_print(line)
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


def _describe(result: CheckinResult | RedeemResult) -> str:
    retcode = result.get("retcode")
    message = result["message"]
    return f"[{retcode}] {message}" if retcode is not None else message


def _checkin_failures(checkin_results: CheckinResults) -> list[str]:
    return [
        f"{account} · {game.value.name} · {_describe(result)}"
        for account, games in checkin_results.items()
        for game, result in games.items()
        if not result["success"] and result.get("status") != "no_character"
    ]


def _redeem_failures(redeem_results: RedemptionResults) -> list[str]:
    """Provider rejections (used, expired codes) are normal outcomes, not failures."""
    return [
        f"{account} · {game.value.name} · {region} · {code} · {_describe(result)}"
        for account, games in redeem_results.items()
        for game, regions in games.items()
        for region, codes in regions.items()
        for code, result in codes.items()
        if not result["success"] and result.get("error_kind") != "provider"
    ]


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
    failures: list[str] = []
    for name, cookie_str in sorted(env_accounts.items()):
        try:
            accounts.append(Account.from_cookie_string(name, cookie_str))
        except ValueError as error:
            failures.append(f"{name} · {error}")

    if not accounts:
        display_failures(failures)
        log_error("SYSTEM", SYSTEM_MESSAGES["VALIDATION_NONE_VALID"])
        sys.exit(1)

    async with create_session() as session:
        # Bước 2: Validate cookies
        validation = await validate_accounts(session, accounts)
        valid_accounts = validation.valid_accounts
        failures += validation.errors
        if not valid_accounts:
            display_failures(failures)
            log_error("SYSTEM", SYSTEM_MESSAGES["VALIDATION_ALL_FAILED"])
            sys.exit(1)

        # Bước 3: Check-in + Fetch data song song
        checkin_results, redemption_data = await asyncio.gather(
            run_checkin(session, valid_accounts),
            fetch_redemption_data(session, valid_accounts),
        )

        # Hiển thị checkin ngay (không đợi redeem)
        display_checkin(checkin_results)
        failures += _checkin_failures(checkin_results)

        # Bước 4: Redeem (dựa trên dữ liệu đã fetch)
        cdkeys, account_uids = redemption_data.cdkeys, redemption_data.account_uids
        display_redeem(cdkeys, account_uids, redemption_data.errors)
        failures += redemption_data.errors

        if any(cdkeys.values()):
            redeem_results = await run_redeem_for_all(
                session, valid_accounts, cdkeys, account_uids
            )
            if redeem_results:
                display_redeem_results(redeem_results)
                failures += _redeem_failures(redeem_results)
            else:
                log_print(SYSTEM_MESSAGES["REDEEM_NO_ELIGIBLE"])

    display_result(checkin_results, failures, ctx.elapsed_seconds)
    write_job_summary(checkin_results, failures, ctx.elapsed_seconds)
    if failures:
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
