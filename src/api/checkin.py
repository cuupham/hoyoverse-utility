"""Check-in API - Điểm danh hàng ngày"""

from __future__ import annotations  # Enable forward references for type hints

import asyncio
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiohttp  # Chỉ import khi type checker chạy, không import runtime

from src.config import (
    COOKIE_CHECK_APP_VERSION,
    COOKIE_CHECK_PAGE_INFO,
    PAGE_NAME_HOME,
    PAGE_NAME_HOME_GAME,
    RPC_LANGUAGE,
    URLS,
    SYSTEM_MESSAGES,
)
from src.constants import JSON_SEPARATORS
from src.models.account import Account
from src.models.game import Game
from src.api.client import safe_api_call
from src.utils.helpers import build_rpc_headers


def _cookie_check_source_info(account: Account) -> str:
    """Build x-rpc-source_info cho user_brief_info (theo curl: HomeUserPage, Post, sourceId)."""
    source_id = account.cookies.get("account_id_v2", "")
    return json.dumps(
        {
            "sourceName": "HomeUserPage",
            "sourceType": "Post",
            "sourceId": source_id,
            "sourceArrangement": "",
            "sourceGameId": "",
        },
        separators=JSON_SEPARATORS,
    )


async def check_cookie(session: aiohttp.ClientSession, account: Account) -> dict[str, Any]:
    """Kiểm tra cookie còn hợp lệ không."""
    headers = build_rpc_headers(
        account,
        "hoyolab",
        COOKIE_CHECK_PAGE_INFO,
        PAGE_NAME_HOME,
        _cookie_check_source_info(account),
    )
    headers["x-rpc-app_version"] = COOKIE_CHECK_APP_VERSION

    result = await safe_api_call(session, URLS["check_cookie"], headers)

    if not result["success"]:
        return {"valid": False, "email_mask": None, "error": result["message"]}

    data = result["data"]
    if data.get("retcode") == 0 and data.get("data", {}).get("email_mask"):
        return {"valid": True, "email_mask": data["data"]["email_mask"], "error": None}

    return {"valid": False, "email_mask": None, "error": data.get("message", "Unknown error")}


async def get_checkin_info(session: aiohttp.ClientSession, account: Account, game: Game) -> dict[str, Any]:
    """Kiểm tra đã điểm danh chưa

    Returns:
        {"is_sign": bool, "total_sign_day": int, "error": str | None}
    """
    game_info = game.value

    headers = build_rpc_headers(
        account,
        "act_hoyolab",
        game_info.get_page_info(PAGE_NAME_HOME_GAME),
        PAGE_NAME_HOME_GAME,
        game=game,
    )

    params = {"lang": RPC_LANGUAGE, "act_id": game_info.act_id}

    result = await safe_api_call(session, URLS["checkin_info"][game_info.code], headers, params=params)

    if not result["success"]:
        return {"is_sign": False, "total_sign_day": 0, "error": result["message"]}

    data = result["data"]
    if data.get("retcode") != 0:
        return {"is_sign": False, "total_sign_day": 0, "error": data.get("message")}

    info = data.get("data", {})
    return {"is_sign": info.get("is_sign", False), "total_sign_day": info.get("total_sign_day", 0), "error": None}


async def do_checkin(session: aiohttp.ClientSession, account: Account, game: Game) -> dict[str, Any]:
    """Thực hiện điểm danh

    Returns:
        {"success": bool, "day": int | None, "message": str}
    """
    game_info = game.value

    # Kiểm tra đã điểm danh chưa
    info = await get_checkin_info(session, account, game)

    if info["error"]:
        return {"success": False, "day": None, "message": info["error"]}

    if info["is_sign"]:
        return {"success": True, "day": info["total_sign_day"], "message": SYSTEM_MESSAGES["CHECKIN_ALREADY"]}

    # Thực hiện điểm danh bằng Header và Payload cung cấp từ GameInfo DataClass
    headers = game_info.get_sign_headers(account, PAGE_NAME_HOME_GAME)
    json_data = game_info.get_sign_payload()

    result = await safe_api_call(
        session, URLS["checkin_sign"][game_info.code], headers, json_data=json_data, method="POST"
    )

    if not result["success"]:
        return {"success": False, "day": None, "message": result["message"]}

    data = result["data"]
    if data.get("retcode") == 0:
        # Tối ưu: Nếu response có dữ liệu ngày (một số game có), dùng luôn.
        # Nếu không (như Genshin), ta increment local để tiết kiệm 1 request get_checkin_info.
        day = info["total_sign_day"] + 1
        return {"success": True, "day": day, "message": SYSTEM_MESSAGES["CHECKIN_SUCCESS"]}

    return {"success": False, "day": None, "message": data.get("message", "Unknown error")}


async def run_checkin_for_account(session: aiohttp.ClientSession, account: Account) -> dict[Game, dict]:
    """Chạy check-in cho 1 account với tất cả games

    Returns:
        Dict {Game: result_dict}
    """
    results = {}
    tasks = [do_checkin(session, account, game) for game in Game]

    game_results = await asyncio.gather(*tasks)

    for game, result in zip(Game, game_results):
        results[game] = result

    return results
