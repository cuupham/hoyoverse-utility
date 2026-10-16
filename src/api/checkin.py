"""Check-in API - Điểm danh hàng ngày"""

from __future__ import annotations  # Enable forward references for type hints

import asyncio
import json
from typing import TYPE_CHECKING

from src.api.request_builder import (
    build_page_info,
    build_sign_headers,
    build_sign_payload,
)

if TYPE_CHECKING:
    import aiohttp  # Chỉ import khi type checker chạy, không import runtime

from src.api.client import parse_provider_envelope, request_json
from src.api.request_builder import build_rpc_headers
from src.config import (
    ACCOUNT_PAGE_INFO,
    PAGE_NAME_HOME,
    PAGE_NAME_HOME_GAME,
    RPC_LANGUAGE,
    SYSTEM_MESSAGES,
    URLS,
)
from src.constants import JSON_SEPARATORS
from src.models.account import Account
from src.models.game import Game
from src.models.results import CheckinInfoResult, CheckinResult, CookieValidationResult


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


def _already_claimed_result(info: CheckinInfoResult) -> CheckinResult:
    return CheckinResult(
        success=True,
        status="already_claimed",
        day=info["total_sign_day"],
        message=SYSTEM_MESSAGES["CHECKIN_ALREADY"],
    )


async def _reconcile_sign(
    session: aiohttp.ClientSession, account: Account, game: Game
) -> CheckinResult | None:
    confirmed = await get_checkin_info(session, account, game)
    if confirmed["error"] or not confirmed["is_sign"]:
        return None
    return _already_claimed_result(confirmed)


async def check_cookie(
    session: aiohttp.ClientSession, account: Account
) -> CookieValidationResult:
    """Kiểm tra cookie còn hợp lệ không."""
    headers = build_rpc_headers(
        account,
        "hoyolab",
        ACCOUNT_PAGE_INFO,
        PAGE_NAME_HOME,
        _cookie_check_source_info(account),
    )

    result = await request_json(session, URLS["check_cookie"], headers)

    parsed = parse_provider_envelope(result)
    email = parsed.data.get("email_mask")
    if parsed.success and isinstance(email, str) and email:
        return CookieValidationResult(
            valid=True, status="valid", email_mask=email, error=None
        )
    return CookieValidationResult(
        valid=False,
        status="invalid_credentials" if parsed.retcode == -100 else "check_failed",
        email_mask=None,
        error=parsed.error or SYSTEM_MESSAGES["ERR_INVALID_RESPONSE"],
    )


async def get_checkin_info(
    session: aiohttp.ClientSession, account: Account, game: Game
) -> CheckinInfoResult:
    """Kiểm tra đã điểm danh chưa."""
    game_info = game.value

    headers = build_rpc_headers(
        account,
        "act_hoyolab",
        build_page_info(game_info, PAGE_NAME_HOME_GAME),
        PAGE_NAME_HOME_GAME,
        game=game,
    )

    params = {"lang": RPC_LANGUAGE, "act_id": game_info.act_id}

    result = await request_json(
        session, URLS["checkin_info"][game_info.code], headers, params=params
    )

    parsed = parse_provider_envelope(result)
    if not parsed.success:
        return CheckinInfoResult(
            is_sign=False,
            total_sign_day=0,
            error=parsed.error,
            retcode=parsed.retcode,
            error_kind=parsed.error_kind,
        )
    info = parsed.data
    if (
        type(info.get("is_sign")) is not bool
        or type(info.get("total_sign_day")) is not int
        or info["total_sign_day"] < 0
    ):
        return CheckinInfoResult(
            is_sign=False,
            total_sign_day=0,
            error=SYSTEM_MESSAGES["ERR_INVALID_RESPONSE"],
            retcode=0,
            error_kind="invalid_response",
        )
    return CheckinInfoResult(
        is_sign=info["is_sign"],
        total_sign_day=info["total_sign_day"],
        error=None,
        retcode=0,
    )


async def do_checkin(
    session: aiohttp.ClientSession, account: Account, game: Game
) -> CheckinResult:
    """Thực hiện điểm danh."""
    game_info = game.value

    # Kiểm tra đã điểm danh chưa
    info = await get_checkin_info(session, account, game)

    if info["error"]:
        result = CheckinResult(
            success=False,
            status="no_character" if info.get("retcode") == -10002 else "failed",
            day=None,
            message=info["error"],
            error_kind=info.get("error_kind"),
        )
        retcode = info.get("retcode")
        if retcode is not None:
            result["retcode"] = retcode
        return result

    if info["is_sign"]:
        return _already_claimed_result(info)

    # Build game-specific transport details in the API adapter.
    headers = build_sign_headers(account, game, PAGE_NAME_HOME_GAME)
    json_data = build_sign_payload(game_info)

    sign_result = await request_json(
        session,
        URLS["checkin_sign"][game_info.code],
        headers,
        json_data=json_data,
        params={"lang": RPC_LANGUAGE} if game is Game.GENSHIN else None,
        method="POST",
        retry=False,
    )

    parsed = parse_provider_envelope(sign_result)
    if not parsed.success:
        # A lost response or an already-claimed race can follow an applied sign.
        if (
            parsed.error_kind
            in {"timeout", "network", "http_error", "invalid_json", "invalid_response"}
            or parsed.retcode == -5003
        ):
            reconciled = await _reconcile_sign(session, account, game)
            if reconciled is not None:
                return reconciled
        failed = CheckinResult(
            success=False,
            status="failed",
            day=None,
            message=parsed.error or SYSTEM_MESSAGES["REQUEST_FAILED"],
            error_kind=parsed.error_kind,
        )
        if parsed.retcode is not None:
            failed["retcode"] = parsed.retcode
        return failed

    risk = parsed.data.get("gt_result", parsed.data)
    invalid_risk = not isinstance(risk, dict) or (
        (
            "is_risk" in risk
            and (
                type(risk["is_risk"]) not in {bool, int}
                or risk["is_risk"] not in (0, 1)
            )
        )
        or ("risk_code" in risk and type(risk["risk_code"]) is not int)
        or any(
            key in risk and not isinstance(risk[key], str)
            for key in ("gt", "challenge")
        )
    )
    if invalid_risk:
        reconciled = await _reconcile_sign(session, account, game)
        if reconciled is not None:
            return reconciled
        return CheckinResult(
            success=False,
            status="failed",
            day=None,
            message=SYSTEM_MESSAGES["ERR_INVALID_RESPONSE"],
            error_kind="invalid_response",
        )
    if risk.get("is_risk") or (
        risk.get("risk_code") and risk.get("gt") and risk.get("challenge")
    ):
        return CheckinResult(
            success=False,
            status="challenge",
            day=None,
            message=SYSTEM_MESSAGES["CHECKIN_CHALLENGE"],
            action_required=True,
            retcode=0,
        )
    return CheckinResult(
        success=True,
        status="claimed",
        day=info["total_sign_day"] + 1,
        message=SYSTEM_MESSAGES["CHECKIN_SUCCESS"],
    )


async def run_checkin_for_account(
    session: aiohttp.ClientSession, account: Account
) -> dict[Game, CheckinResult]:
    """Chạy check-in cho 1 account với tất cả games."""
    tasks = [do_checkin(session, account, game) for game in Game]
    game_results = await asyncio.gather(*tasks)
    return dict(zip(Game, game_results))
