"""Redeem Exchange API - preserve provider errors without guessing global expiry."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp

from src.api.client import parse_provider_envelope, request_json
from src.api.request_builder import build_page_info, build_rpc_headers
from src.config import (
    PAGE_NAME_HOME_GAME,
    REDEEM_DELAY_SECONDS,
    REDEEM_LANG,
    SYSTEM_MESSAGES,
    URLS,
)
from src.models.account import Account
from src.models.game import REGIONS, Game
from src.models.results import RedeemResult
from src.utils.timekeeping import unix_ms


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
        return RedeemResult(
            success=False,
            message=SYSTEM_MESSAGES["REDEEM_UNKNOWN_REGION"].format(
                region_code=region_code
            ),
            error_kind="invalid_response",
        )

    headers = build_rpc_headers(
        account,
        "hoyolab",
        build_page_info(game_info, PAGE_NAME_HOME_GAME),
        page_name=PAGE_NAME_HOME_GAME,
    )
    params: dict[str, str | int] = {
        "cdkey": cdkey,
        "game_biz": game_info.game_biz,
        "lang": REDEEM_LANG,
        "region": region_value,
        "t": unix_ms(),
        "uid": uid,
    }
    result = await request_json(
        session,
        URLS["redeem"][game_info.code],
        headers,
        params=params,
        retry=False,
    )

    parsed = parse_provider_envelope(result, allow_null_data=True)
    if parsed.success:
        return RedeemResult(success=True, message=SYSTEM_MESSAGES["REDEEM_SUCCESS"])
    failed = RedeemResult(
        success=False,
        message=parsed.error or SYSTEM_MESSAGES["REQUEST_FAILED"],
        error_kind=parsed.error_kind,
    )
    if parsed.retcode is not None:
        failed["retcode"] = parsed.retcode
    return failed


async def redeem_codes_for_region(
    session: aiohttp.ClientSession,
    account: Account,
    game: Game,
    region_code: str,
    uid: str,
    codes: list[str],
) -> dict[str, RedeemResult]:
    """Attempt every code in a region, sequentially and with the configured delay."""
    results: dict[str, RedeemResult] = {}

    for i, code in enumerate(codes):
        result = await exchange_cdkey(session, account, game, region_code, uid, code)
        results[code] = result

        # Delay giữa mỗi code (trừ code cuối)
        if i < len(codes) - 1:
            await asyncio.sleep(REDEEM_DELAY_SECONDS)

    return results


async def _redeem_game_for_account(
    session: aiohttp.ClientSession,
    account: Account,
    game: Game,
    codes: list[str],
    game_uids: dict[str, str],
) -> dict[str, dict[str, RedeemResult]]:
    """Redeem codes cho 1 game với tất cả regions.

    Regions run sequentially; a rejection in one region does not suppress another.
    """
    game_results: dict[str, dict[str, RedeemResult]] = {}

    for region, uid in game_uids.items():
        region_result = await redeem_codes_for_region(
            session, account, game, region, uid, codes
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

    Strategy: Games PARALLEL, Regions SEQUENTIAL.
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
