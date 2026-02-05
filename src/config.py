"""Centralized configuration - Tất cả constants và settings"""
import os

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
    'hoyolab': {
        'origin': 'https://www.hoyolab.com',
        'referer': 'https://www.hoyolab.com/',
    },
    'act_hoyolab': {
        'origin': 'https://act.hoyolab.com',
        'referer': 'https://act.hoyolab.com/',
    },
}

# ==================== API URLs ====================
URLS = {
    # Cookie validation
    'check_cookie': 'https://bbs-api-os.hoyolab.com/community/misc/wapi/account/user_brief_info',
    
    # Check-in
    'checkin_info': {
        'gs': 'https://sg-hk4e-api.hoyolab.com/event/sol/info',
        'sr': 'https://sg-public-api.hoyolab.com/event/luna/hkrpg/os/info',
        'zzz': 'https://sg-public-api.hoyolab.com/event/luna/zzz/os/info',
    },
    'checkin_sign': {
        'gs': 'https://sg-hk4e-api.hoyolab.com/event/sol/sign?lang=en-us',
        'sr': 'https://sg-public-api.hoyolab.com/event/luna/hkrpg/os/sign',
        'zzz': 'https://sg-public-api.hoyolab.com/event/luna/zzz/os/sign',
    },
    
    # CDKeys
    'fetch_cdkeys': 'https://bbs-api-os.hoyolab.com/community/painter/wapi/circle/channel/guide/material',
    
    # UID
    'fetch_uid': 'https://api-account-os.hoyolab.com/binding/api/getUserGameRolesByLtoken',
    
    # Redeem
    'redeem': {
        'gs': 'https://public-operation-hk4e.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl',
        'sr': 'https://public-operation-hkrpg.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl',
        'zzz': 'https://public-operation-nap.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl',
    },
}

# ==================== SETTINGS ====================
SEMAPHORE_LIMIT = 20      # Max concurrent requests
REDEEM_DELAY = 5          # Seconds between redeem codes
REQUEST_TIMEOUT = 30      # Total request timeout
CONNECT_TIMEOUT = 10      # Connection timeout
MAX_RETRIES = 3           # Retry attempts
RATE_LIMIT_DELAY = 5      # Seconds to wait when rate limited (429)
MIN_UID_LENGTH = 6        # UIDs shorter than this are masked entirely
DEFAULT_TIMEZONE = "Asia/Saigon"  # Khớp với curl của bạn

# Connection pool (client session)
CONNECTOR_LIMIT = 30
CONNECTOR_LIMIT_PER_HOST = 10

# Logger: default output mode khi LOG_LEVEL không set hoặc không hợp lệ
DEFAULT_LOG_LEVEL = "human"

# Display: từ khóa nhận diện "đã điểm danh trước đó" trong message
CHECKIN_ALREADY_SIGNED_KEYWORD = "trước đó"

# Cookie check API (user_brief_info) - x-rpc-app_version
# Lấy từ env COOKIE_CHECK_APP_VERSION; nếu không set thì gửi rỗng (API vẫn chấp nhận).
# Khi có phương pháp lấy version (vd iTunes API, roadmap) có thể set env hoặc cập nhật logic ở đây.
def _get_cookie_check_app_version() -> str:
    v = os.environ.get("COOKIE_CHECK_APP_VERSION", "").strip()
    return v if v else ""


COOKIE_CHECK_APP_VERSION = _get_cookie_check_app_version()

# ==================== REDEEM MESSAGES (i18n ready) ====================
REDEEM_MESSAGES = {
    0: "Thành công",
    -2001: "Code không tồn tại",
    -2003: "Code đã sử dụng",
    -2011: "Chưa đủ rank",
    -2016: "Code đã hết hạn",
    -2017: "Đã sử dụng hoặc không đủ điều kiện (Level/Rank)",
}

# Retcodes để skip trong 1 region (không thử các codes còn lại trong region này)
# -2011: Chưa đủ rank - rank được tính per-account, không cần thử code khác
SKIP_REMAINING_IN_REGION = {-2011}

# Retcodes để skip toàn cục (không thử ở các regions khác nữa)
# -2016: Code đã hết hạn - hết hạn ở mọi nơi
# -2001: Code không tồn tại - không tồn tại ở đâu cả
SKIP_GLOBALLY_RETCODES = {-2016, -2001}

# Combined: cả 2 đều skip codes còn lại trong region hiện tại
SKIP_REMAINING_RETCODES = SKIP_REMAINING_IN_REGION | SKIP_GLOBALLY_RETCODES
