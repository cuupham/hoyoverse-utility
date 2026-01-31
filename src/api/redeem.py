"""Redeem API - Fetch CDKeys, UIDs và Exchange codes"""
import asyncio
import aiohttp
from typing import Any

from src.config import COMMON_HEADERS, ORIGINS, URLS, REDEEM_DELAY, REDEEM_MESSAGES, SKIP_REMAINING_RETCODES, SKIP_GLOBALLY_RETCODES, DEFAULT_TIMEZONE
from src.models.account import Account
from src.models.game import Game, REGIONS
from src.api.client import safe_api_call
from src.utils.helpers import current_hour, rpc_weekday, unix_ms


async def fetch_cdkeys(
    session: aiohttp.ClientSession, 
    account: Account, 
    game: Game
) -> list[str]:
    """Fetch danh sách CDKeys cho 1 game
    
    Args:
        session: aiohttp ClientSession
        account: Account để lấy cookies
        game: Game enum
        
    Returns:
        List các CDKey codes
    """
    game_info = game.value
    
    headers = {
        **COMMON_HEADERS,
        **ORIGINS["act_hoyolab"],
        "Cookie": account.cookie_str,
        "x-rpc-client_type": "4",
        "x-rpc-device_id": account.mhy_uuid,
        "x-rpc-hour": current_hour(),
        "x-rpc-language": "en-us",
        "x-rpc-lrsag": "",
        "x-rpc-page_info": game_info.get_page_info(""),
        "x-rpc-page_name": "",
        "x-rpc-show-translated": "false",
        "x-rpc-source_info": '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
        "x-rpc-sys_version": "Windows NT 10.0",
        "x-rpc-timezone": DEFAULT_TIMEZONE,
        "x-rpc-weekday": rpc_weekday(),
    }
    
    params = {"game_id": game_info.game_id}
    
    result = await safe_api_call(session, URLS['fetch_cdkeys'], headers, params=params)
    
    if not result["success"]:
        return []
    
    data = result["data"]
    if data.get("retcode") != 0:
        return []
    
    # Trích xuất codes từ response
    codes = [
        bonus["exchange_code"]
        for module in data.get("data", {}).get("modules", [])
        if (group := module.get("exchange_group"))
        for bonus in group.get("bonuses", [])
        if bonus.get("exchange_code")
    ]
    
    return codes


async def fetch_all_cdkeys(
    session: aiohttp.ClientSession,
    account: Account
) -> dict[Game, list[str]]:
    """Fetch tất cả CDKeys cho 3 games song song
    
    Returns:
        Dict {Game: [codes]}
    """
    tasks = [fetch_cdkeys(session, account, game) for game in Game]
    results = await asyncio.gather(*tasks)
    
    cdkeys = {}
    for game, codes in zip(Game, results):
        cdkeys[game] = codes
    
    return cdkeys


async def fetch_uid(
    session: aiohttp.ClientSession,
    account: Account,
    game: Game,
    region_code: str
) -> str | None:
    """Fetch UID của player cho game+region cụ thể
    
    Returns:
        UID string hoặc None nếu không có
    """
    game_info = game.value
    region_value = REGIONS[game].get(region_code)
    
    if not region_value:
        return None
    
    headers = {
        **COMMON_HEADERS,
        **ORIGINS["hoyolab"],
        "Cookie": account.cookie_str,
        "x-rpc-client_type": "4",
        "x-rpc-device_id": account.mhy_uuid,
        "x-rpc-hour": current_hour(),
        "x-rpc-language": "en-us",
        "x-rpc-lrsag": "",
        "x-rpc-page_info": game_info.get_page_info("HomeGamePage"),
        "x-rpc-page_name": "HomeGamePage",
        "x-rpc-show-translated": "false",
        "x-rpc-source_info": '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
        "x-rpc-sys_version": "Windows NT 10.0",
        "x-rpc-timezone": DEFAULT_TIMEZONE,
        "x-rpc-weekday": rpc_weekday(),
    }
    
    params = {
        "region": region_value,
        "game_biz": game_info.game_biz
    }
    
    result = await safe_api_call(session, URLS['fetch_uid'], headers, params=params)
    
    if not result["success"]:
        return None
    
    data = result["data"]
    if data.get("retcode") != 0:
        return None
    
    uid_list = data.get("data", {}).get("list", [])
    if uid_list:
        return uid_list[0].get("game_uid")
    
    return None


async def fetch_all_uids(
    session: aiohttp.ClientSession,
    account: Account
) -> dict[Game, dict[str, str]]:
    """Fetch tất cả UIDs cho account (3 games × 4 regions)
    
    Returns:
        Dict {Game: {region: uid}}
    """
    uids: dict[Game, dict[str, str]] = {game: {} for game in Game}
    
    # Tạo tất cả tasks
    tasks = []
    task_info = []  # Để track game và region
    
    for game in Game:
        for region_code in REGIONS[game].keys():
            tasks.append(fetch_uid(session, account, game, region_code))
            task_info.append((game, region_code))
    
    # Chạy tất cả song song
    results = await asyncio.gather(*tasks)
    
    for (game, region), uid in zip(task_info, results):
        if uid:
            uids[game][region] = uid
    
    return uids


async def exchange_cdkey(
    session: aiohttp.ClientSession,
    account: Account,
    game: Game,
    region_code: str,
    uid: str,
    cdkey: str
) -> dict[str, Any]:
    """Nhập 1 redeem code
    
    Returns:
        {"success": bool, "message": str}
    """
    game_info = game.value
    region_value = REGIONS[game].get(region_code)
    
    headers = {
        **COMMON_HEADERS,
        **ORIGINS["hoyolab"],
        "Cookie": account.cookie_str,
        "x-rpc-client_type": "4",
        "x-rpc-device_id": account.mhy_uuid,
        "x-rpc-hour": current_hour(),
        "x-rpc-language": "en-us",
        "x-rpc-lrsag": "",
        "x-rpc-page_info": game_info.get_page_info("HomeGamePage"),
        "x-rpc-page_name": "HomeGamePage",
        "x-rpc-show-translated": "false",
        "x-rpc-source_info": '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
        "x-rpc-sys_version": "Windows NT 10.0",
        "x-rpc-timezone": DEFAULT_TIMEZONE,
        "x-rpc-weekday": rpc_weekday(),
    }
    
    params = {
        "cdkey": cdkey,
        "game_biz": game_info.game_biz,
        "lang": "en",
        "region": region_value,
        "t": unix_ms(),
        "uid": uid
    }
    
    result = await safe_api_call(
        session, 
        URLS['redeem'][game_info.code], 
        headers, 
        params=params
    )
    
    if not result["success"]:
        return {"success": False, "message": result["message"]}
    
    data = result["data"]
    retcode = data.get("retcode", -1)
    
    if retcode == 0:
        return {"success": True, "message": REDEEM_MESSAGES[0]}
    
    return {
        "success": False, 
        "message": data.get("message") or REDEEM_MESSAGES.get(retcode, f"Error {retcode}"),
        "skip_remaining": retcode in SKIP_REMAINING_RETCODES,
        "retcode": retcode,  # Return retcode to allow cross-region skip logic
    }


async def redeem_codes_for_region(
    session: aiohttp.ClientSession,
    account: Account,
    game: Game,
    region_code: str,
    uid: str,
    codes: list[str],
    globally_expired_codes: set[str] | None = None,
) -> dict[str, dict]:
    """Redeem tất cả codes cho 1 game+region (tuần tự với delay)
    
    Args:
        session: aiohttp ClientSession
        account: Account object
        game: Game enum
        region_code: Region code (asia, usa, euro, tw)
        uid: Player UID for this region
        codes: List of codes to redeem
        globally_expired_codes: Shared set tracking codes that are expired/invalid globally.
                                If a code is in this set, skip it (don't try).
                                If a code returns -2016/-2001, add it to this set.
    
    Returns:
        Dict {code: result}
    """
    results = {}
    
    if globally_expired_codes is None:
        globally_expired_codes = set()
    
    for i, code in enumerate(codes):
        # Skip if this code is already known to be globally expired/invalid
        if code in globally_expired_codes:
            results[code] = {
                "success": False,
                "message": "⏭ Đã skip (expired/invalid từ region trước)",
                "skipped": True,
            }
            continue
        
        result = await exchange_cdkey(session, account, game, region_code, uid, code)
        results[code] = result
        
        # Check if this code should be marked as globally expired
        retcode = result.get("retcode")
        if retcode in SKIP_GLOBALLY_RETCODES:
            globally_expired_codes.add(code)
        
        # Check if should skip remaining codes (e.g., -2011 = chưa đủ rank)
        if result.get("skip_remaining"):
            break
        
        # Delay 5s giữa mỗi code (trừ code cuối)
        if i < len(codes) - 1:
            await asyncio.sleep(REDEEM_DELAY)
    
    return results


async def _redeem_game_for_account(
    session: aiohttp.ClientSession,
    account: Account,
    game: Game,
    codes: list[str],
    game_uids: dict[str, str],
) -> dict[str, dict]:
    """Helper: Redeem codes cho 1 game với tất cả regions (tuần tự trong game)
    
    Regions chạy TUẦN TỰ để share expired_codes giữa các regions.
    
    Returns:
        Dict {region: {code: result}}
    """
    # Shared set to track globally expired/invalid codes for this game
    # This enables cross-region skip: if code expires in Asia, skip in America/Euro
    globally_expired_codes: set[str] = set()
    
    game_results = {}
    
    # Process regions SEQUENTIALLY to enable cross-region skip
    for region, uid in game_uids.items():
        region_result = await redeem_codes_for_region(
            session, account, game, region, uid, codes,
            globally_expired_codes=globally_expired_codes
        )
        game_results[region] = region_result
    
    return game_results


async def run_redeem_for_account(
    session: aiohttp.ClientSession,
    account: Account,
    cdkeys: dict[Game, list[str]],
    uids: dict[Game, dict[str, str]]
) -> dict:
    """Chạy redeem cho 1 account với tất cả games/regions
    
    Processing strategy:
    - Games: PARALLEL (mỗi game có codes riêng, không cần share)
    - Regions trong 1 Game: SEQUENTIAL (để share expired codes giữa regions)
    
    Args:
        session: aiohttp ClientSession
        account: Account object
        cdkeys: Dict {Game: [codes]}
        uids: Dict {Game: {region: uid}}
        
    Returns:
        Dict kết quả
    """
    # Collect games that have both codes and UIDs
    games_to_redeem = []
    
    for game in Game:
        codes = cdkeys.get(game, [])
        game_uids = uids.get(game, {})
        
        if codes and game_uids:
            games_to_redeem.append((game, codes, game_uids))
    
    if not games_to_redeem:
        return {}
    
    # Run ALL GAMES in PARALLEL
    # Each game will process its regions sequentially (for cross-region skip)
    tasks = [
        _redeem_game_for_account(session, account, game, codes, game_uids)
        for game, codes, game_uids in games_to_redeem
    ]
    
    game_results = await asyncio.gather(*tasks)
    
    # Combine results
    results = {}
    for (game, _, _), game_result in zip(games_to_redeem, game_results):
        results[game] = game_result
    
    return results
