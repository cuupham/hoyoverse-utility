"""Helper functions - Các hàm tiện ích"""
import os
import time
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.account import Account

from src.config import (
    COMMON_HEADERS,
    DEFAULT_TIMEZONE,
    ORIGINS,
    RPC_CLIENT_TYPE,
    RPC_LANGUAGE,
    RPC_SHOW_TRANSLATED,
    RPC_SYS_VERSION,
)


def current_hour() -> str:
    """Trả về giờ hiện tại dạng 2 chữ số (00-23)"""
    return f'{datetime.now().hour:02}'


def rpc_weekday() -> str:
    """Trả về thứ trong tuần (1=Monday, 7=Sunday)"""
    return str(datetime.now().isoweekday())


def unix_ms() -> int:
    """Trả về timestamp hiện tại dạng milliseconds"""
    return int(time.time() * 1000)


def get_accounts_from_env() -> dict[str, str]:
    """Lấy tất cả biến môi trường bắt đầu bằng ACC_.

    Returns:
        Dict {name: cookie_string} cho các accounts tìm được.
    """
    return {k: v for k, v in os.environ.items() if k.startswith("ACC_") and (v or "").strip()}


def build_rpc_headers(
    account: "Account",
    origin_key: str,
    page_info: str,
    page_name: str,
    source_info: str = '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
) -> dict[str, str]:
    """Tạo headers chung cho các API RPC (fetch CDKeys, UID, redeem).

    Args:
        account: Account chứa cookie và device id.
        origin_key: Key trong ORIGINS ('hoyolab' hoặc 'act_hoyolab').
        page_info: Chuỗi JSON x-rpc-page_info.
        page_name: Giá trị x-rpc-page_name.
        source_info: Chuỗi JSON x-rpc-source_info.

    Returns:
        Dict headers đủ cho request.
    """
    return {
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
