"""Centralized configuration - Tất cả constants và settings"""

import json
import os

from src.constants import JSON_SEPARATORS
from src.utils.headers import DYNAMIC_HEADERS

# ==================== COMMON HEADERS ====================
COMMON_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9,vi-VN;q=0.8,vi;q=0.7",
    **DYNAMIC_HEADERS,
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
URLS = {
    # Cookie validation
    "check_cookie": "https://bbs-api-os.hoyolab.com/community/misc/wapi/account/user_brief_info",
    # Check-in
    "checkin_info": {
        "gs": "https://sg-hk4e-api.hoyolab.com/event/sol/info",
        "sr": "https://sg-public-api.hoyolab.com/event/luna/hkrpg/os/info",
        "zzz": "https://sg-public-api.hoyolab.com/event/luna/zzz/os/info",
    },
    "checkin_sign": {
        "gs": "https://sg-hk4e-api.hoyolab.com/event/sol/sign?lang=en-us",
        "sr": "https://sg-public-api.hoyolab.com/event/luna/hkrpg/os/sign",
        "zzz": "https://sg-public-api.hoyolab.com/event/luna/zzz/os/sign",
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
REDEEM_DELAY = 5  # Seconds between redeem codes
REQUEST_TIMEOUT = 30  # Total request timeout
MIN_REQUEST_TIMEOUT = 15  # Floor timeout per attempt (prevent premature timeouts)
CONNECT_TIMEOUT = 10  # Connection timeout
MAX_RETRIES = 3  # Retry attempts
RATE_LIMIT_DELAY = 5  # Seconds to wait when rate limited (429)
MIN_UID_LENGTH = 6  # UIDs shorter than this are masked entirely
DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"  # IANA standard (Asia/Saigon is deprecated)

# Connection pool (client session)
CONNECTOR_LIMIT = 30
CONNECTOR_LIMIT_PER_HOST = 10

# Display: độ rộng dòng header/footer (số ký tự "=")
HEADER_WIDTH = 50

# ==================== RPC HEADER VALUES (single source - dùng trong checkin, helpers, API) ====================
RPC_LANGUAGE = "en-us"
RPC_CLIENT_TYPE = "4"
RPC_SYS_VERSION = "Windows NT 10.0"
RPC_SHOW_TRANSLATED = "false"
# Page names cho x-rpc-page_name / get_page_info
PAGE_NAME_HOME_GAME = "HomeGamePage"
PAGE_NAME_HOME = "HomePage"
# Lang param cho redeem API (khác RPC_LANGUAGE)
REDEEM_LANG = "en"

# Cookie check: page_info static (account-wide, không gắn game)
COOKIE_CHECK_PAGE_INFO = json.dumps(
    {"pageName": PAGE_NAME_HOME, "pageType": "", "pageId": "", "pageArrangement": "", "gameId": ""},
    separators=JSON_SEPARATORS,
)


# Cookie check API (user_brief_info) - x-rpc-app_version
# Lấy từ env; rỗng nếu không set (API vẫn chấp nhận).
COOKIE_CHECK_APP_VERSION = os.environ.get("COOKIE_CHECK_APP_VERSION", "").strip()

# ==================== REDEEM MESSAGES (i18n ready) ====================
REDEEM_MESSAGES = {
    0: "Thành công",
    -2001: "Code không tồn tại",
    -2003: "Code đã sử dụng",
    -2011: "Chưa đủ rank",
    -2016: "Code đã hết hạn",
    -2017: "Đã sử dụng",
}

# Message hiển thị khi skip code đã biết expired/invalid từ region trước (single source cho redeem + display)
REDEEM_SKIP_MESSAGE_EXPIRED = "⏭ Đã skip (expired/invalid từ region trước)"

# Retcodes để skip trong 1 region (không thử các codes còn lại trong region này)
# -2011: Chưa đủ rank - rank được tính per-account, không cần thử code khác
SKIP_REMAINING_IN_REGION = {-2011}

# Retcodes để skip toàn cục (không thử ở các regions khác nữa)
# -2016: Code đã hết hạn - hết hạn ở mọi nơi
# -2001: Code không tồn tại - không tồn tại ở đâu cả
SKIP_GLOBALLY_RETCODES = {-2016, -2001}

# Combined: cả 2 đều skip codes còn lại trong region hiện tại
SKIP_REMAINING_RETCODES = SKIP_REMAINING_IN_REGION | SKIP_GLOBALLY_RETCODES

# ==================== SYSTEM_MESSAGES ====================
SYSTEM_MESSAGES = {
    "CHECKIN_SUCCESS": "Điểm danh thành công",
    "CHECKIN_ALREADY": "Đã điểm danh trước đó",
    "VALIDATION_VALID": "Hợp lệ",
    "VALIDATION_ALL_FAILED": "Tất cả cookies đều không hợp lệ!",
    "VALIDATION_NONE_FOUND": "Không tìm thấy account nào trong environment variables!",
    "VALIDATION_NONE_VALID": "Không có account nào hợp lệ để tiếp tục!",
    "REDEEM_NO_CODES": "Không có codes nào để redeem",
    "REDEEM_NO_UIDS": "Tất cả accounts đều không có UID - không thể redeem!",
    "SYSTEM_NO_CODES": "Không có codes",
    "SYSTEM_CODES_FOUND": "codes",
    "SYSTEM_NO_UIDS": "Không có UID nào",
    # Display section headers
    "SECTION_CHECKIN": "--- CHECK-IN ---",
    "SECTION_REDEEM": "--- REDEEM CODE ---",
    "LABEL_CDKEYS": "CDKeys:",
    "LABEL_UIDS": "UIDs:",
    # Checkin status (short display)
    "CHECKIN_ALREADY_SHORT": "✓ Đã điểm danh",
    "CHECKIN_NO_CHARACTER": "— Chưa tạo nhân vật",
    "ERR_NETWORK": "Network connection failed",
    "ERR_TIMEOUT": "Request timed out",
    "ERR_INVALID_JSON": "Response not JSON",
    "ERR_UNKNOWN_SECURE": "Request failed (details hidden for security)",
}
