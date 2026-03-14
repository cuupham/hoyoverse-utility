"""Helper functions - Các hàm tiện ích"""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from src.models.account import Account
    from src.models.game import Game

from src.config import (
    COMMON_HEADERS,
    DEFAULT_TIMEZONE,
    ORIGINS,
    RPC_CLIENT_TYPE,
    RPC_LANGUAGE,
    RPC_SHOW_TRANSLATED,
    RPC_SYS_VERSION,
)
from src.constants import DEFAULT_SOURCE_INFO

# Cache ZoneInfo object - tạo 1 lần, dùng xuyên suốt
TZ = ZoneInfo(DEFAULT_TIMEZONE)


def current_hour() -> str:
    """Trả về giờ hiện tại dạng 2 chữ số (00-23) theo DEFAULT_TIMEZONE"""
    return f"{datetime.now(TZ).hour:02}"


def rpc_weekday() -> str:
    """Trả về thứ trong tuần (1=Monday, 7=Sunday) theo DEFAULT_TIMEZONE"""
    return str(datetime.now(TZ).isoweekday())


def unix_ms() -> int:
    """Trả về timestamp hiện tại dạng milliseconds"""
    return int(time.time() * 1000)


def get_accounts_from_env() -> dict[str, str]:
    """Lấy tất cả biến môi trường bắt đầu bằng ACC_."""
    return {k: v for k, v in os.environ.items() if k.startswith("ACC_") and (v or "").strip()}


def build_rpc_headers(
    account: Account,
    origin_key: str,
    page_info: str,
    page_name: str,
    source_info: str = DEFAULT_SOURCE_INFO,
    game: Game | None = None,
) -> dict[str, str]:
    """Tạo headers chung cho các API RPC (fetch CDKeys, UID, redeem)."""
    headers = {
        **COMMON_HEADERS,
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

    # Game-specific: thêm signgame header cho Star Rail/ZZZ
    if game and game.value.signgame:
        headers["x-rpc-signgame"] = game.value.signgame

    return headers
