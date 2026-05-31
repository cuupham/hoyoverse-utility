"""Redeem Fetch API - Fetch CDKeys và UIDs từ HoYoLab"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp

from src.config import ALL_ROLES_PAGE_INFO, PAGE_NAME_HOME, URLS
from src.models.account import Account
from src.models.game import Game, GAME_BY_BIZ, REGION_CODE_BY_VALUE
from src.api.client import safe_api_call
from src.utils.helpers import build_rpc_headers


async def fetch_cdkeys(
    session: aiohttp.ClientSession,
    account: Account,
    game: Game,
) -> list[str]:
    """Fetch danh sách CDKeys cho 1 game.

    Returns:
        List các CDKey codes.
    """
    game_info = game.value
    headers = build_rpc_headers(
        account,
        "act_hoyolab",
        game_info.get_page_info(""),
        page_name="",
    )
    params = {"game_id": game_info.game_id}

    result = await safe_api_call(session, URLS["fetch_cdkeys"], headers, params=params)

    if not result["success"]:
        return []

    data = result["data"]
    if data.get("retcode") != 0:
        return []

    # Trích xuất codes từ response
    return [
        bonus["exchange_code"]
        for module in data.get("data", {}).get("modules", [])
        if (group := module.get("exchange_group"))
        for bonus in group.get("bonuses", [])
        if bonus.get("exchange_code")
    ]


async def fetch_all_cdkeys(session: aiohttp.ClientSession, account: Account) -> dict[Game, list[str]]:
    """Fetch tất cả CDKeys cho 3 games song song."""
    tasks = [fetch_cdkeys(session, account, game) for game in Game]
    results = await asyncio.gather(*tasks)
    return dict(zip(Game, results))


async def fetch_all_uids(session: aiohttp.ClientSession, account: Account) -> dict[Game, dict[str, str]]:
    """Fetch tất cả UIDs cho account trong 1 request.

    getUserGameRolesByLtoken (không kèm region/game_biz) trả về MỌI game role
    account đang sở hữu. Trước đây loop 3 games × N regions = nhiều request rỗng;
    giờ chỉ 1 request rồi map ngược (game_biz → Game, region_value → region_code).

    Returns:
        dict[Game, dict[region_code, uid]] — game/region account không chơi sẽ rỗng.
    """
    uids: dict[Game, dict[str, str]] = {game: {} for game in Game}

    headers = build_rpc_headers(
        account,
        "hoyolab",
        ALL_ROLES_PAGE_INFO,
        page_name=PAGE_NAME_HOME,
    )

    result = await safe_api_call(session, URLS["fetch_uid"], headers)

    if not result["success"]:
        return uids

    data = result["data"]
    if data.get("retcode") != 0:
        return uids

    for role in data.get("data", {}).get("list", []):
        game = GAME_BY_BIZ.get(role.get("game_biz"))
        if game is None:
            continue  # Game không được hỗ trợ (vd Honkai 3rd, Tears of Themis)

        region_code = REGION_CODE_BY_VALUE.get((game, role.get("region")))
        uid = role.get("game_uid")
        if region_code and uid:
            uids[game][region_code] = uid

    return uids
