"""Redeem Exchange API - Exchange CDKeys cho rewards

NOTE: Regions trong 1 game chạy TUẦN TỰ để share globally_expired_codes.
Nếu đổi sang parallel, PHẢI dùng asyncio.Lock để bảo vệ shared set.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp

from src.config import (
    PAGE_NAME_HOME_GAME,
    REDEEM_DELAY,
    REDEEM_LANG,
    REDEEM_MESSAGES,
    REDEEM_SKIP_MESSAGE_EXPIRED,
    SKIP_GLOBALLY_RETCODES,
    SKIP_REMAINING_RETCODES,
    URLS,
)
from src.utils.logger import log_info
from src.models.account import Account
from src.models.game import Game, REGIONS
from src.models.types import RedeemResult
from src.api.client import safe_api_call
from src.utils.helpers import build_rpc_headers, unix_ms


async def exchange_cdkey(
    session: aiohttp.ClientSession,
    account: Account,
    game: Game,
    region_code: str,
    uid: str,
    cdkey: str,
) -> RedeemResult:
    """Nhập 1 redeem code."""
    game_info = game.value
    region_value = REGIONS[game].get(region_code)

    if not region_value:
        return RedeemResult(success=False, message=f"Unknown region: {region_code}")

    headers = build_rpc_headers(
        account,
        "hoyolab",
        game_info.get_page_info(PAGE_NAME_HOME_GAME),
        page_name=PAGE_NAME_HOME_GAME,
    )
    params = {
        "cdkey": cdkey,
        "game_biz": game_info.game_biz,
        "lang": REDEEM_LANG,
        "region": region_value,
        "t": unix_ms(),
        "uid": uid,
    }
    result = await safe_api_call(
        session,
        URLS["redeem"][game_info.code],
        headers,
        params=params,
    )

    if not result["success"]:
        return RedeemResult(success=False, message=result["message"])

    data = result["data"]
    retcode = data.get("retcode", -1)

    if retcode == 0:
        return RedeemResult(success=True, message=REDEEM_MESSAGES[0])

    return RedeemResult(
        success=False,
        message=REDEEM_MESSAGES.get(retcode) or data.get("message") or f"Error {retcode}",
        skip_remaining=retcode in SKIP_REMAINING_RETCODES,
        retcode=retcode,
    )


async def redeem_codes_for_region(
    session: aiohttp.ClientSession,
    account: Account,
    game: Game,
    region_code: str,
    uid: str,
    codes: list[str],
    globally_expired_codes: set[str] | None = None,
) -> dict[str, RedeemResult]:
    """Redeem tất cả codes cho 1 game+region (tuần tự với delay).

    Args:
        globally_expired_codes: Shared set tracking codes expired/invalid globally.
            Nếu code nằm trong set -> skip. Nếu trả về -2016/-2001 -> thêm vào set.
    """
    results: dict[str, RedeemResult] = {}

    if globally_expired_codes is None:
        globally_expired_codes = set()

    for i, code in enumerate(codes):
        # Skip code đã biết expired/invalid từ region trước
        if code in globally_expired_codes:
            results[code] = RedeemResult(
                success=False,
                message=REDEEM_SKIP_MESSAGE_EXPIRED,
                skipped=True,
            )
            continue

        result = await exchange_cdkey(session, account, game, region_code, uid, code)
        results[code] = result

        # Mark globally expired nếu cần
        retcode = result.get("retcode")
        if retcode in SKIP_GLOBALLY_RETCODES:
            globally_expired_codes.add(code)

        # Skip remaining codes trong region (vd: -2011 chưa đủ rank)
        if result.get("skip_remaining"):
            break

        # Delay giữa mỗi code (trừ code cuối)
        if i < len(codes) - 1:
            await asyncio.sleep(REDEEM_DELAY)

    return results


async def _redeem_game_for_account(
    session: aiohttp.ClientSession,
    account: Account,
    game: Game,
    codes: list[str],
    game_uids: dict[str, str],
) -> dict[str, dict[str, RedeemResult]]:
    """Redeem codes cho 1 game với tất cả regions.

    Regions chạy TUẦN TỰ để share expired_codes giữa các regions.
    """
    regions = list(game_uids.keys())
    log_info(
        account.name,
        f"Redeeming {game.value.name}: {len(codes)} code(s) × {len(regions)} region(s) ({', '.join(regions)})",
    )

    globally_expired_codes: set[str] = set()
    game_results: dict[str, dict[str, RedeemResult]] = {}

    for region, uid in game_uids.items():
        region_result = await redeem_codes_for_region(
            session, account, game, region, uid, codes, globally_expired_codes=globally_expired_codes
        )
        game_results[region] = region_result

    return game_results


async def run_redeem_for_account(
    session: aiohttp.ClientSession,
    account: Account,
    cdkeys: dict[Game, list[str]],
    uids: dict[Game, dict[str, str]],
) -> dict[Game, dict[str, dict[str, RedeemResult]]]:
    """Chạy redeem cho 1 account với tất cả games/regions.

    Strategy: Games PARALLEL (codes riêng), Regions SEQUENTIAL (share expired codes).
    """
    games_to_redeem = []

    for game in Game:
        codes = cdkeys.get(game, [])
        game_uids = uids.get(game, {})
        if codes and game_uids:
            games_to_redeem.append((game, codes, game_uids))

    if not games_to_redeem:
        return {}

    tasks = [
        _redeem_game_for_account(session, account, game, codes, game_uids)
        for game, codes, game_uids in games_to_redeem
    ]

    game_results = await asyncio.gather(*tasks)

    return {game: result for (game, _, _), result in zip(games_to_redeem, game_results)}
