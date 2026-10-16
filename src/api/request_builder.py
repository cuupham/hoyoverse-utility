"""Construct consistent browser/RPC headers and game-specific sign requests."""

import json
import re
from typing import Literal

from fake_useragent import UserAgent

from src.config import (
    COMMON_HEADERS,
    DEFAULT_TIMEZONE,
    ORIGINS,
    PAGE_NAME_HOME_GAME,
    RPC_CLIENT_TYPE,
    RPC_LANGUAGE,
    RPC_SHOW_TRANSLATED,
    RPC_SYS_VERSION,
)
from src.constants import DEFAULT_CHROME_VERSION, DEFAULT_SOURCE_INFO, JSON_SEPARATORS
from src.models.account import Account
from src.models.game import Game, GameInfo
from src.utils.timekeeping import current_hour, rpc_weekday


def generate_browser_headers() -> dict[str, str]:
    """Choose one Windows desktop Chrome profile matching all declared hints."""
    fallback = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{DEFAULT_CHROME_VERSION}.0.0.0 Safari/537.36"
    )
    user_agent = UserAgent(
        browsers=["Chrome"], os=["Windows"], platforms=["desktop"], fallback=fallback
    ).chrome
    if "Windows NT 10.0" not in user_agent or "Mobile" in user_agent:
        user_agent = fallback
    match = re.search(r"Chrome/(\d+)", user_agent)
    version = match.group(1) if match else DEFAULT_CHROME_VERSION
    return {
        "user-agent": user_agent,
        "sec-ch-ua": f'"Chromium";v="{version}", "Google Chrome";v="{version}", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }


BROWSER_HEADERS = generate_browser_headers()


def build_page_info(game_info: GameInfo, page_name: str = PAGE_NAME_HOME_GAME) -> str:
    return json.dumps(
        {
            "pageName": page_name,
            "pageType": game_info.page_type,
            "pageId": "",
            "pageArrangement": "Hot" if page_name == PAGE_NAME_HOME_GAME else "",
            "gameId": game_info.game_id,
        },
        separators=JSON_SEPARATORS,
    )


def build_rpc_headers(
    account: Account,
    origin_key: Literal["hoyolab", "act_hoyolab"],
    page_info: str,
    page_name: str,
    source_info: str = DEFAULT_SOURCE_INFO,
    game: Game | None = None,
) -> dict[str, str]:
    headers = {
        **COMMON_HEADERS,
        **BROWSER_HEADERS,
        **ORIGINS[origin_key],
        "Cookie": account.cookie_str,
        "x-rpc-client_type": RPC_CLIENT_TYPE,
        "x-rpc-device_id": account.mhy_uuid,
        "x-rpc-hour": current_hour(),
        "x-rpc-language": RPC_LANGUAGE,
        "x-rpc-lrsag": "",
        "x-rpc-page_info": page_info,
        "x-rpc-page_name": page_name,
        "x-rpc-show-translated": RPC_SHOW_TRANSLATED,
        "x-rpc-source_info": source_info,
        "x-rpc-sys_version": RPC_SYS_VERSION,
        "x-rpc-timezone": DEFAULT_TIMEZONE,
        "x-rpc-weekday": rpc_weekday(),
    }
    if game:
        headers["x-rpc-signgame"] = game.value.sign_game
    return headers


def build_sign_payload(game_info: GameInfo) -> dict[str, str]:
    payload = {"act_id": game_info.act_id}
    if game_info.code != "gs":
        payload["lang"] = RPC_LANGUAGE
    return payload


def build_sign_headers(account: Account, game: Game, page_name: str) -> dict[str, str]:
    headers = build_rpc_headers(
        account,
        "act_hoyolab",
        build_page_info(game.value, page_name),
        page_name,
        game=game,
    )
    if game is Game.GENSHIN:
        headers.update(
            {
                "content-type": "application/json;charset=UTF-8",
                "x-rpc-app_version": "",
                "x-rpc-device_name": "",
            }
        )
    return headers
