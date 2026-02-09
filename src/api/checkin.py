"""Check-in API - Điểm danh hàng ngày"""
from __future__ import annotations  # Enable forward references for type hints

import asyncio
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiohttp  # Chỉ import khi type checker chạy, không import runtime

from src.config import (
    COMMON_HEADERS,
    COOKIE_CHECK_APP_VERSION,
    COOKIE_CHECK_PAGE_INFO,
    DEFAULT_TIMEZONE,
    ORIGINS,
    PAGE_NAME_HOME,
    PAGE_NAME_HOME_GAME,
    RPC_CLIENT_TYPE,
    RPC_LANGUAGE,
    RPC_PLATFORM,
    RPC_SHOW_TRANSLATED,
    RPC_SYS_VERSION,
    URLS,
)
from src.constants import JSON_SEPARATORS
from src.models.account import Account
from src.models.game import Game
from src.api.client import safe_api_call
from src.utils.helpers import current_hour, rpc_weekday


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
    """Kiểm tra cookie còn hợp lệ không.

    Headers khớp curl thực tế: origin www.hoyolab.com, x-rpc-device_id = _HYVUUID,
    x-rpc-app_version, source_info HomeUserPage/Post với sourceId = account_id_v2.

    Args:
        session: aiohttp ClientSession.
        account: Account object.

    Returns:
        {"valid": bool, "email_mask": str | None, "error": str | None}
    """
    headers = {
        **COMMON_HEADERS,
        **ORIGINS["hoyolab"],
        "Cookie": account.cookie_str,
        "x-rpc-app_version": COOKIE_CHECK_APP_VERSION,
        "x-rpc-client_type": RPC_CLIENT_TYPE,
        "x-rpc-device_id": account.hyv_uuid,
        "x-rpc-hour": current_hour(),
        "x-rpc-language": RPC_LANGUAGE,
        "x-rpc-lrsag": "",
        "x-rpc-page_info": COOKIE_CHECK_PAGE_INFO,
        "x-rpc-page_name": PAGE_NAME_HOME,
        "x-rpc-show-translated": RPC_SHOW_TRANSLATED,
        "x-rpc-source_info": _cookie_check_source_info(account),
        "x-rpc-sys_version": RPC_SYS_VERSION,
        "x-rpc-timezone": DEFAULT_TIMEZONE,
        "x-rpc-weekday": rpc_weekday(),
    }
    result = await safe_api_call(session, URLS["check_cookie"], headers)
    
    if not result["success"]:
        return {"valid": False, "email_mask": None, "error": result["message"]}
    
    data = result["data"]
    if data.get("retcode") == 0 and data.get("data", {}).get("email_mask"):
        return {"valid": True, "email_mask": data["data"]["email_mask"], "error": None}
    
    return {"valid": False, "email_mask": None, "error": data.get("message", "Unknown error")}


async def get_checkin_info(
    session: aiohttp.ClientSession, 
    account: Account, 
    game: Game
) -> dict[str, Any]:
    """Kiểm tra đã điểm danh chưa
    
    Returns:
        {"is_sign": bool, "total_sign_day": int, "error": str | None}
    """
    game_info = game.value
    
    # Headers tối giản theo pattern curl thành công
    headers = {
        **COMMON_HEADERS,
        **ORIGINS["act_hoyolab"],
        "Cookie": account.cookie_str,
        "x-rpc-page_info": game_info.get_page_info(PAGE_NAME_HOME_GAME),
    }
    
    if game_info.signgame:  # Star Rail / ZZZ
        headers["x-rpc-signgame"] = game_info.signgame
    else:  # Genshin
        headers["x-rpc-lrsag"] = ""
    
    params = {"lang": RPC_LANGUAGE, "act_id": game_info.act_id}
    
    result = await safe_api_call(
        session, 
        URLS['checkin_info'][game_info.code], 
        headers,
        params=params
    )
    
    if not result["success"]:
        return {"is_sign": False, "total_sign_day": 0, "error": result["message"]}
    
    data = result["data"]
    if data.get("retcode") != 0:
        return {"is_sign": False, "total_sign_day": 0, "error": data.get("message")}
    
    info = data.get("data", {})
    return {
        "is_sign": info.get("is_sign", False),
        "total_sign_day": info.get("total_sign_day", 0),
        "error": None
    }


async def do_checkin(
    session: aiohttp.ClientSession, 
    account: Account, 
    game: Game
) -> dict[str, Any]:
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
        return {"success": True, "day": info["total_sign_day"], "message": "Đã điểm danh trước đó"}
    
    # Thực hiện điểm danh
    headers = {
        **COMMON_HEADERS,
        **ORIGINS["act_hoyolab"],
        "Cookie": account.cookie_str,
        "x-rpc-page_info": game_info.get_page_info(PAGE_NAME_HOME_GAME),
    }
    
    if game_info.signgame:  # Star Rail / ZZZ
        headers["x-rpc-client_type"] = RPC_CLIENT_TYPE
        headers["x-rpc-platform"] = RPC_PLATFORM
        headers["x-rpc-signgame"] = game_info.signgame
        json_data = {"act_id": game_info.act_id, "lang": RPC_LANGUAGE}
    else:  # Genshin
        headers["content-type"] = "application/json;charset=UTF-8"
        headers["x-rpc-app_version"] = ""
        headers["x-rpc-device_id"] = account.hyv_uuid
        headers["x-rpc-device_name"] = ""
        headers["x-rpc-lrsag"] = ""
        headers["x-rpc-page_info"] = game_info.get_page_info(PAGE_NAME_HOME_GAME)
        headers["x-rpc-platform"] = RPC_PLATFORM
        json_data = {"act_id": game_info.act_id}
    
    result = await safe_api_call(
        session,
        URLS['checkin_sign'][game_info.code],
        headers,
        json_data=json_data,
        method="POST"
    )
    
    if not result["success"]:
        return {"success": False, "day": None, "message": result["message"]}
    
    data = result["data"]
    if data.get("retcode") == 0:
        # Lấy lại info để có số ngày mới
        new_info = await get_checkin_info(session, account, game)
        day = new_info["total_sign_day"] if not new_info["error"] else info["total_sign_day"] + 1
        return {"success": True, "day": day, "message": "Điểm danh thành công"}
    
    return {"success": False, "day": None, "message": data.get("message", "Unknown error")}


async def run_checkin_for_account(
    session: aiohttp.ClientSession,
    account: Account
) -> dict[Game, dict]:
    """Chạy check-in cho 1 account với tất cả games
    
    Returns:
        Dict {Game: result_dict}
    """
    results = {}
    tasks = []
    
    for game in Game:
        tasks.append(do_checkin(session, account, game))
    
    game_results = await asyncio.gather(*tasks)
    
    for game, result in zip(Game, game_results):
        results[game] = result
    
    return results
