"""Redeem Fetch API - Fetch CDKeys và UIDs từ HoYoLab"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp

from src.api.client import parse_provider_envelope, request_json
from src.api.request_builder import build_page_info, build_rpc_headers
from src.config import PAGE_NAME_HOME, SYSTEM_MESSAGES, URLS
from src.models.account import Account
from src.models.game import GAME_BY_BIZ, REGION_CODE_BY_VALUE, Game
from src.models.results import ProviderResult


async def fetch_cdkeys(
    session: aiohttp.ClientSession,
    account: Account,
    game: Game,
) -> ProviderResult[list[str]]:
    """Fetch danh sách CDKeys cho 1 game.

    Returns a typed outcome; successful empty material is not an API failure.
    """
    game_info = game.value
    headers = build_rpc_headers(
        account,
        "hoyolab",
        build_page_info(game_info, ""),
        page_name="",
    )
    params = {"game_id": game_info.game_id}

    result = await request_json(session, URLS["fetch_cdkeys"], headers, params=params)

    parsed = parse_provider_envelope(result)
    if not parsed.success:
        return ProviderResult(
            [], error=parsed.error, retcode=parsed.retcode, error_kind=parsed.error_kind
        )
    modules = parsed.data.get("modules")
    if not isinstance(modules, list):
        return ProviderResult(
            [],
            error=SYSTEM_MESSAGES["ERR_INVALID_RESPONSE"],
            retcode=0,
            error_kind="invalid_response",
        )
    codes: list[str] = []
    for module in modules:
        if not isinstance(module, dict):
            return ProviderResult(
                [],
                error=SYSTEM_MESSAGES["ERR_INVALID_RESPONSE"],
                retcode=0,
                error_kind="invalid_response",
            )
        group = module.get("exchange_group")
        if group is None:
            continue
        if not isinstance(group, dict):
            return ProviderResult(
                [],
                error=SYSTEM_MESSAGES["ERR_INVALID_RESPONSE"],
                retcode=0,
                error_kind="invalid_response",
            )
        bonuses = group.get("bonuses")
        if bonuses is None:
            continue
        if not isinstance(bonuses, list):
            return ProviderResult(
                [],
                error=SYSTEM_MESSAGES["ERR_INVALID_RESPONSE"],
                retcode=0,
                error_kind="invalid_response",
            )
        for bonus in bonuses:
            if not isinstance(bonus, dict) or not isinstance(
                bonus.get("exchange_code", ""), str
            ):
                return ProviderResult(
                    [],
                    error=SYSTEM_MESSAGES["ERR_INVALID_RESPONSE"],
                    retcode=0,
                    error_kind="invalid_response",
                )
            code = bonus.get("exchange_code", "").strip()
            if code and code not in codes:
                codes.append(code)
    return ProviderResult(codes, retcode=0)


async def fetch_all_uids(
    session: aiohttp.ClientSession, account: Account
) -> ProviderResult[dict[Game, dict[str, str]]]:
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
        build_page_info(page_name=PAGE_NAME_HOME),
        page_name=PAGE_NAME_HOME,
    )

    result = await request_json(session, URLS["fetch_uid"], headers)

    parsed = parse_provider_envelope(result)
    if not parsed.success:
        return ProviderResult(
            uids,
            error=parsed.error,
            retcode=parsed.retcode,
            error_kind=parsed.error_kind,
        )
    roles = parsed.data.get("list")
    if not isinstance(roles, list):
        return ProviderResult(
            uids,
            error=SYSTEM_MESSAGES["ERR_INVALID_RESPONSE"],
            retcode=0,
            error_kind="invalid_response",
        )
    for role in roles:
        if not isinstance(role, dict) or not isinstance(role.get("game_biz"), str):
            return ProviderResult(
                {game: {} for game in Game},
                error=SYSTEM_MESSAGES["ERR_INVALID_RESPONSE"],
                retcode=0,
                error_kind="invalid_response",
            )
        game = GAME_BY_BIZ.get(role["game_biz"])
        if game is None:
            continue  # Game không được hỗ trợ (vd Honkai 3rd, Tears of Themis)

        region = role.get("region")
        uid = role.get("game_uid")
        if not isinstance(region, str) or not isinstance(uid, str) or not uid.isdigit():
            return ProviderResult(
                {game: {} for game in Game},
                error=SYSTEM_MESSAGES["ERR_INVALID_RESPONSE"],
                retcode=0,
                error_kind="invalid_response",
            )
        region_code = REGION_CODE_BY_VALUE.get((game, region))
        if region_code and uid:
            uids[game][region_code] = uid

    return ProviderResult(uids, retcode=0)
