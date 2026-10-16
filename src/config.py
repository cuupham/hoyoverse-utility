"""Centralized configuration - Tất cả constants và settings"""

from typing import TypedDict

# ==================== COMMON HEADERS ====================
COMMON_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9,vi-VN;q=0.8,vi;q=0.7",
    "dnt": "1",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "priority": "u=1, i",
}

# ==================== ORIGINS ====================
ORIGINS = {
    "hoyolab": {
        "origin": "https://www.hoyolab.com",
        "referer": "https://www.hoyolab.com/",
    },
    "act_hoyolab": {
        "origin": "https://act.hoyolab.com",
        "referer": "https://act.hoyolab.com/",
    },
}


# ==================== API URLs ====================
# Typed endpoint groups keep shared and per-game routes distinct.
class GameEndpoints(TypedDict):
    gs: str
    sr: str
    zzz: str


class ApiUrls(TypedDict):
    check_cookie: str
    checkin_info: GameEndpoints
    checkin_sign: GameEndpoints
    fetch_cdkeys: str
    fetch_uid: str
    redeem: GameEndpoints


URLS: ApiUrls = {
    # Cookie validation
    "check_cookie": "https://bbs-api-os.hoyolab.com/community/misc/wapi/account/user_brief_info",
    # Check-in
    "checkin_info": {
        "gs": "https://sg-act-public-api.hoyolab.com/event/sol/info",
        "sr": "https://sg-act-public-api.hoyolab.com/event/luna/hkrpg/os/info",
        "zzz": "https://sg-act-public-api.hoyolab.com/event/luna/zzz/os/info",
    },
    "checkin_sign": {
        "gs": "https://sg-act-public-api.hoyolab.com/event/sol/sign",
        "sr": "https://sg-act-public-api.hoyolab.com/event/luna/hkrpg/os/sign",
        "zzz": "https://sg-act-public-api.hoyolab.com/event/luna/zzz/os/sign",
    },
    # CDKeys
    "fetch_cdkeys": "https://bbs-api-os.hoyolab.com/community/painter/wapi/circle/channel/guide/material",
    # UID
    "fetch_uid": "https://api-account-os.hoyolab.com/binding/api/getUserGameRolesByLtoken",
    # Redeem
    "redeem": {
        "gs": "https://public-operation-hk4e.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl",
        "sr": "https://public-operation-hkrpg.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl",
        "zzz": "https://public-operation-nap.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl",
    },
}

# ==================== SETTINGS ====================
SEMAPHORE_LIMIT = 20  # Max concurrent requests
REDEEM_DELAY_SECONDS = 5  # Seconds between redeem codes
REQUEST_TIMEOUT_SECONDS = 30  # Maximum timeout for an individual attempt
# Floor timeout per attempt (prevent premature timeouts)
MIN_ATTEMPT_TIMEOUT_SECONDS = 15
CONNECT_TIMEOUT_SECONDS = 10  # Connection timeout
MAX_ATTEMPTS = 3  # Total attempts, including the initial request
RATE_LIMIT_DELAY_SECONDS = 5  # Seconds to wait when rate limited (429)
DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"  # IANA standard (Asia/Saigon is deprecated)

# Connection pool (client session)
CONNECTOR_LIMIT = 30
CONNECTOR_LIMIT_PER_HOST = 10

# ==================== RPC HEADER VALUES (single source - dùng trong request_builder) ====================
RPC_LANGUAGE = "en-us"
RPC_CLIENT_TYPE = "4"
RPC_SYS_VERSION = "Windows NT 10.0"
RPC_SHOW_TRANSLATED = "false"
# Page names used by the request builder
PAGE_NAME_HOME_GAME = "HomeGamePage"
PAGE_NAME_HOME = "HomePage"
# Lang param cho redeem API (khác RPC_LANGUAGE)
REDEEM_LANG = "en"

# ==================== PROVIDER RETCODES ====================
RETCODE_INVALID_CREDENTIALS = -100
RETCODE_NO_CHARACTER = -10002
RETCODE_ALREADY_SIGNED = -5003

# x-rpc-app_version cố tình KHÔNG gửi cho cookie check (user_brief_info): đã
# verify trên account thật, header này không ảnh hưởng kết quả.

# ==================== SYSTEM_MESSAGES ====================
SYSTEM_MESSAGES = {
    "REQUEST_FAILED": "Request failed",
    "REDEEM_SUCCESS": "Thành công",
    "REDEEM_UNKNOWN_REGION": "Unknown region: {region_code}",
    "CHECKIN_SUCCESS": "Điểm danh thành công",
    "CHECKIN_ALREADY": "Đã điểm danh trước đó",
    "CHECKIN_CHALLENGE": "Cần xác minh trên trang điểm danh HoYoLAB",
    "VALIDATION_ALL_FAILED": "Không thể xác thực account nào; xem lỗi từng account.",
    "VALIDATION_NONE_FOUND": "Không tìm thấy account nào trong environment variables!",
    "VALIDATION_NONE_VALID": "Không có account nào hợp lệ để tiếp tục!",
    "REDEEM_NO_ELIGIBLE": "Không có account nào có UID cho game đang có code",
    "SYSTEM_NO_CODES": "Không có codes",
    "SYSTEM_NO_UIDS": "Không có UID nào",
    # Display: two-space gap separates a section name from its inline detail
    "HEADER": "HOYOLAB AUTO TOOL · {time} · trace {trace}",
    "SECTION_ACCOUNTS": "ACCOUNTS  {valid}/{total} hợp lệ",
    "SECTION_CHECKIN": "CHECK-IN",
    "SECTION_REDEEM": "REDEEM",
    "REDEEM_NONE": "REDEEM  không có code mới",
    "REDEEM_FETCH_FAILED": "REDEEM  không lấy được dữ liệu (xem LỖI)",
    "LABEL_UIDS": "UIDs:",
    "FAILURE_SCOPE": "LỖI",
    "CHECKIN_LEGEND": "{claimed} vừa điểm danh · {already} đã điểm danh trước · {skipped} chưa có nhân vật · {error} lỗi",
    "RESULT_LINE": "KẾT QUẢ  {verdict} · {ok} điểm danh · {skipped} chưa có nhân vật · {errors} lỗi · {seconds:.1f}s",
    "ERR_NETWORK": "Network connection failed",
    "ERR_TIMEOUT": "Request timed out",
    "ERR_INVALID_JSON": "Response not JSON",
    "ERR_INVALID_RESPONSE": "Unexpected API response structure",
    "ERR_UNKNOWN_SECURE": "Request failed (details hidden for security)",
}

# ==================== STATUS LABELS ====================
# ASCII keeps table columns aligned in the GitHub log font.
STATUS_OK = "ok"
STATUS_SKIPPED = "--"
STATUS_ERROR = "ERR"
CHECKIN_DAY_LABEL = "d{day}"
VERDICT_OK = "OK"
VERDICT_FAILED = "FAILED"

# Check-in status -> (log table cell, job summary cell)
CHECKIN_LABELS = {
    "claimed": (CHECKIN_DAY_LABEL, "✅ Ngày {day}"),
    "already_claimed": (STATUS_OK, "✅ Đã điểm danh"),
    "no_character": (STATUS_SKIPPED, "➖ Chưa có nhân vật"),
    "challenge": (STATUS_ERROR, "❌ Cần xác minh"),
    "failed": (STATUS_ERROR, "❌ Lỗi"),
}
