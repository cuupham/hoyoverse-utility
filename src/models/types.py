"""Type definitions - TypedDict cho tất cả API return types

Single source of truth cho cấu trúc dữ liệu trả về giữa các module.
"""

from typing import Any, Required, TypedDict


# ==================== API Client ====================
class ApiResult(TypedDict, total=False):
    """Kết quả từ safe_api_call"""

    success: Required[bool]
    data: dict[str, Any]
    error: str
    message: str


# ==================== Cookie Validation ====================
class CookieCheckResult(TypedDict):
    """Kết quả validate cookie"""

    valid: bool
    email_mask: str | None
    error: str | None


# ==================== Check-in ====================
class CheckinInfoResult(TypedDict, total=False):
    """Kết quả kiểm tra trạng thái check-in"""

    is_sign: Required[bool]
    total_sign_day: Required[int]
    error: str | None
    retcode: int | None


class CheckinResult(TypedDict, total=False):
    """Kết quả thực hiện check-in"""

    success: Required[bool]
    message: Required[str]
    day: int | None
    retcode: int


# ==================== Redeem ====================
class RedeemResult(TypedDict, total=False):
    """Kết quả redeem 1 code"""

    success: Required[bool]
    message: Required[str]
    skip_remaining: bool
    skipped: bool
    retcode: int
