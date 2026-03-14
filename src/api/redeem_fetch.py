"""Redeem Fetch API - Fetch CDKeys và UIDs từ HoYoLab"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp

from src.config import PAGE_NAME_HOME_GAME, URLS
from src.models.account import Account
from src.models.game import Game, REGIONS
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


async def fetch_uid(
    session: aiohttp.ClientSession, account: Account, game: Game, region_code: str
) -> str | None:
    """Fetch UID của player cho game+region cụ thể."""
    game_info = game.value
    region_value = REGIONS[game].get(region_code)

    if not region_value:
        return None

    headers = build_rpc_headers(
        account,
        "hoyolab",
        game_info.get_page_info(PAGE_NAME_HOME_GAME),
        page_name=PAGE_NAME_HOME_GAME,
    )
    params = {
        "region": region_value,
        "game_biz": game_info.game_biz,
    }
    result = await safe_api_call(session, URLS["fetch_uid"], headers, params=params)

    if not result["success"]:
        return None

    data = result["data"]
    if data.get("retcode") != 0:
        return None

    uid_list = data.get("data", {}).get("list", [])
    if uid_list:
        return uid_list[0].get("game_uid")

    return None


async def fetch_all_uids(session: aiohttp.ClientSession, account: Account) -> dict[Game, dict[str, str]]:
    """Fetch tất cả UIDs cho account (3 games x N regions)."""
    uids: dict[Game, dict[str, str]] = {game: {} for game in Game}

    tasks = []
    task_info = []

    for game in Game:
        for region_code in REGIONS[game]:
            tasks.append(fetch_uid(session, account, game, region_code))
            task_info.append((game, region_code))

    results = await asyncio.gather(*tasks)

    for (game, region), uid in zip(task_info, results):
        if uid:
            uids[game][region] = uid

    return uids
