# System Architecture & Flows

## 4. Luồng xử lý chính (Main Flow)

```
┌─────────────────────────────────────────────────────────────┐
│                    KHỞI ĐỘNG CHƯƠNG TRÌNH                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  BƯỚC 1: Đọc tất cả biến môi trường ACC_*                   │
│  ├─ Nếu KHÔNG có account nào → In lỗi & THOÁT              │
│  └─ Nếu CÓ → Tiếp tục                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  BƯỚC 2: Validate cookies (đa luồng - N accounts)           │
│  ├─ Gọi API kiểm tra từng cookie                            │
│  ├─ Lọc ra danh sách accounts hợp lệ                        │
│  ├─ Nếu KHÔNG có account hợp lệ → In lỗi & THOÁT           │
│  └─ Nếu CÓ → Tiếp tục với danh sách hợp lệ                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  BƯỚC 3: Thực thi Song song theo Từng cụm (Silent Phase)     │
│  │                                                          │
│  │  Tất cả các hàm API chỉ trả về data (Dictionary),        │
│  │  KHÔNG in log trực tiếp ra console để tránh xen kẽ.      │
│  │                                                          │
│  ├─[Cụm A] CHECK-IN: N accounts × 3 games (Song song)       │
│  └─[Cụm B] REDEEM Logic:                                    │
│  │  1. Fetch CDKeys (Song song 3 games)                     │
│  │  2. Fetch UIDs (Song song N accounts)                    │
│  │  3. Exchange codes (Parallel games, Sequential regions)   │
│  │                                                          │
│  │  **LƯU Ý BẢO MẬT:** Bước 3.1 và 3.2 chạy TUẦN TỰ để tránh│
│  │  tạo Spike requests lớn (Spam API), giúp tool an toàn    │
│  │  và tránh bị HoYoLab hệ thống anti-bot gắn cờ.           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  BƯỚC 4: Hiển thị báo cáo kết quả (Sequenced Display)       │
│  │                                                          │
│  │  Dữ liệu từ Bước 3 được gom lại và in theo thứ tự:       │
│  │  1. In toàn bộ Section CHECK-IN                          │
│  │  2. In toàn bộ Section REDEEM CODE                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  BƯỚC 5: Kết thúc chương trình                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Chiến lược đa luồng

### 6.1. Check-in

```
Accounts: [acc_1, acc_2, acc_3, acc_4]
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
[acc_1, acc_2, acc_3, acc_4] × [Genshin, StarRail, ZZZ]
                    │
                    ▼
            4 × 3 = 12 luồng song song
```

### 6.2. Fetch UIDs

```
Accounts × Games × Regions = N × 3 × 4 luồng

Ví dụ: 4 accounts → 4 × 3 × 4 = 48 luồng song song
```

### 6.3. Redeem Codes

**Chiến lược xử lý:**
- **Games**: SONG SONG (mỗi game có codes riêng, API riêng)
- **Regions trong 1 Game**: TUẦN TỰ (để share `expired_codes` giữa regions)
- **Codes trong 1 Region**: TUẦN TỰ với delay 5s

```
Mỗi account:
┌─── Genshin ────────────────────────────────────┐
│  Asia → America → Europe → TW (TUẦN TỰ)       │
│  share expired_codes giữa regions             │
└────────────────────────────────────────────────┘
┌─── Star Rail ──────────────────────────────────┐
│  Asia → America → Europe → TW (TUẦN TỰ)       │  ← 3 Games chạy SONG SONG
│  share expired_codes giữa regions             │
└────────────────────────────────────────────────┘
┌─── ZZZ ────────────────────────────────────────┐
│  Asia → America → Europe → TW (TUẦN TỰ)       │
│  share expired_codes giữa regions             │
└────────────────────────────────────────────────┘
```

### 6.4. Cross-region Skip Logic

**Mục đích**: Nếu code hết hạn/không tồn tại ở region đầu tiên, không cần thử ở các regions khác.

```python
# src/config.py
# Retcodes chỉ skip trong region hiện tại
SKIP_REMAINING_IN_REGION = {-2011}  # Chưa đủ rank

# Retcodes skip toàn cục (không thử ở regions khác)
SKIP_GLOBALLY_RETCODES = {-2016, -2001}  # Expired, không tồn tại

# Combined
SKIP_REMAINING_RETCODES = SKIP_REMAINING_IN_REGION | SKIP_GLOBALLY_RETCODES
```

**Ví dụ:**
```
Game Genshin:
  Region Asia:
    CODE1: ✓ Thành công
    CODE2: -2016 (hết hạn) → Thêm vào globally_expired_codes
  
  Region America:
    CODE1: ✓ Thành công
    CODE2: ⏭ Đã skip (expired/invalid từ region trước) → TIẾT KIỆM API call! (message từ config.REDEEM_SKIP_MESSAGE_EXPIRED)
  
  Region Europe:
    CODE1: ✓ Thành công
    CODE2: ⏭ Đã skip (expired/invalid từ region trước)
```

---

## 9. Project Structure

```
hoyoverse-utility/
├── .github/
│   └── workflows/
│       ├── hoyo-flow.yml       # GitHub Actions workflow (daily run)
│       └── test.yml            # CI: chạy tests + coverage trên mỗi push/PR
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point - orchestration flow
│   ├── config.py               # Cấu hình tập trung (URLs, ORIGINS, RPC_*, SYSTEM_MESSAGES, settings)
│   ├── constants.py            # Giá trị không phụ thuộc module khác (JSON_SEPARATORS, DEFAULT_CHROME_VERSION, DEFAULT_SOURCE_INFO)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py           # HTTP client wrapper (retry, semaphore, anti-detection)
│   │   ├── checkin.py          # Check-in APIs (check_cookie, get_checkin_info, do_checkin)
│   │   ├── redeem_fetch.py     # Fetch CDKeys & UIDs (read-only APIs)
│   │   └── redeem_exchange.py  # Exchange redeem codes (write APIs, delay 5s)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── account.py          # Account model (immutable dataclass)
│   │   ├── game.py             # Game enum, GameInfo, REGIONS mapping
│   │   └── types.py            # TypedDict definitions (ApiResult, CheckinResult, RedeemResult, ...)
│   └── utils/
│       ├── __init__.py
│       ├── display.py          # UI formatting & display logic (tables, reports)
│       ├── headers.py          # Dynamic User-Agent headers (fake-useragent)
│       ├── helpers.py          # Helper functions (build_rpc_headers, current_hour, ...)
│       ├── logger.py           # Logging utilities (trace_id, ForceFlushStreamHandler, log_print)
│       └── security.py         # Mask sensitive data (mask_uid)
├── tests/                      # Test suite
│   ├── auth/                   # Local auth files (không push lên repo)
│   ├── api-health/             # API health check scripts
│   ├── integration/            # End-to-end integration tests
│   ├── scripts/                # Debug API scripts
│   ├── unit/                   # Unit tests
│   │   ├── test_checkin.py     # Test logic điểm danh
│   │   ├── test_core.py        # Test models, utils, session isolation
│   │   ├── test_coverage_audit.py
│   │   ├── test_display.py     # Test UI formatting (display module)
│   │   ├── test_fetch_cdkeys.py
│   │   ├── test_fetch_uids.py  # Test fetch UIDs (game × region)
│   │   ├── test_main_flow.py   # Test main orchestration flow
│   │   └── test_redeem.py      # Test đổi code & cross-region skip
│   └── conftest.py             # Fixtures & Mock data chung
├── requirements/               # Tài liệu kỹ thuật
│   ├── SPEC.md                 # System Specification
│   ├── architecture.md         # Kiến trúc hệ thống (file này)
│   ├── api_contract.md         # API Contract
│   ├── error_codes.md          # Error Handling & Codes
│   └── raw.require.md          # Raw requirements gốc
├── pytest.ini                  # Pytest config (root level)
├── requirements.txt
└── README.md
```

### 9.1. Security Utilities - Mask Sensitive Data

> [!WARNING]
> **BẮT BUỘC** mask sensitive data trong logs để tránh lộ thông tin khi chạy trên public repo.

> [!NOTE]
> **Email không cần mask thủ công** - API đã trả về `email_mask` sẵn (VD: `u***34@gmail.com`)

```python
# src/utils/security.py

def mask_uid(uid: str | int | None) -> str:
    """
    Mask UID: 123456789 → 123***789
    """
    if not uid:
        return "***"
    uid = str(uid)
    if len(uid) <= MIN_UID_LENGTH:
        return "***"
    return f"{uid[:3]}***{uid[-3:]}"
```

**Sử dụng:**
```python
from utils.security import mask_uid
from utils.logger import log_info

# Email đã được mask từ API response
email_mask = response["data"]["email_mask"]  # u***34@gmail.com

# UID cần mask thủ công
log_info(acc.name, f"Hợp lệ ({email_mask})")
log_info(acc.name, f"Genshin: UID {mask_uid(uid)}")

# Output:
# 20/01/2026 07:50:58 [INFO] [ACC_1] Hợp lệ (u***34@gmail.com)
# 20/01/2026 07:50:58 [INFO] [ACC_1] Genshin Impact: Character UID 123***789
```

---

### 9.2. Centralized Config - Gom tất cả Constants

- **`src/config.py`:** URLs, ORIGINS, COMMON_HEADERS, settings (timeout, retry, semaphore), RPC header values (`RPC_LANGUAGE`, `RPC_CLIENT_TYPE`, `RPC_PLATFORM`, `RPC_SYS_VERSION`, `RPC_SHOW_TRANSLATED`), page names (`PAGE_NAME_HOME`, `PAGE_NAME_HOME_GAME`), `REDEEM_LANG`, `COOKIE_CHECK_PAGE_INFO`, `REDEEM_MESSAGES`, `SYSTEM_MESSAGES`, `SKIP_REMAINING_IN_REGION`, `SKIP_GLOBALLY_RETCODES`, `REDEEM_SKIP_MESSAGE_EXPIRED`, `DEFAULT_TIMEZONE`, `HEADER_WIDTH` (display), `DEFAULT_LOG_LEVEL`, `CHECKIN_ALREADY_SIGNED_KEYWORD`, v.v.
- **`src/constants.py`:** Giá trị không phụ thuộc module khác: `JSON_SEPARATORS`, `DEFAULT_CHROME_VERSION`, `DEFAULT_SOURCE_INFO` (default x-rpc-source_info cho `build_rpc_headers`).
- **`src/models/game.py`:** Game enum, GameInfo (với `get_sign_payload()`, `get_sign_headers()`), REGIONS mapping.
- **`src/models/types.py`:** TypedDict definitions (`ApiResult`, `CookieCheckResult`, `CheckinInfoResult`, `CheckinResult`, `RedeemResult`) — Single Source of Truth cho cấu trúc dữ liệu giữa các module.
- **`src/utils/display.py`:** Tập trung tất cả UI formatting/display logic (`display_checkin()`, `display_cdkeys()`, `display_uids()`, `display_redeem_results()`) — tách từ main.py.

```python
# src/models/game.py - Game, GameInfo, REGIONS

from src.config import PAGE_NAME_HOME_GAME
from src.constants import JSON_SEPARATORS

@dataclass(frozen=True)
class GameInfo:
    """Thông tin của 1 game"""
    code: str
    name: str
    game_id: str
    act_id: str
    game_biz: str
    signgame: str | None
    page_type: str = ""

    def get_page_info(self, page_name: str = PAGE_NAME_HOME_GAME) -> str:
        """Sinh chuỗi JSON cho x-rpc-page_info với game_id và page_type động"""
        return json.dumps({...}, separators=JSON_SEPARATORS)

class Game(Enum):
    """Enum các game được hỗ trợ - Type-safe, IDE autocomplete"""
    GENSHIN = GameInfo(
        code='gs',
        name='Genshin Impact',
        game_id='2',
        act_id='e202102251931481',
        game_biz='hk4e_global',
        signgame=None,
    )
    STAR_RAIL = GameInfo(
        code='sr',
        name='Honkai: Star Rail',
        game_id='6',
        act_id='e202303301540311',
        game_biz='hkrpg_global',
        signgame='hkrpg',
    )
    ZZZ = GameInfo(
        code='zzz',
        name='Zenless Zone Zero',
        game_id='8',
        act_id='e202406031448091',
        game_biz='nap_global',
        signgame='zzz',
        page_type='46',
    )

# ==================== REGIONS ====================
# Key = region code (thống nhất trong code: asia, usa, euro, tw)
# Value = chuỗi gửi API (mỗi game khác nhau).
REGIONS: dict[Game, dict[str, str]] = {
    Game.GENSHIN: {
        'asia': 'os_asia',
        'usa': 'os_usa',
        'euro': 'os_euro',
        'tw': 'os_cht',
    },
    Game.STAR_RAIL: {
        'asia': 'prod_official_asia',
        'usa': 'prod_official_usa',
        'euro': 'prod_official_eur',
        'tw': 'prod_official_cht',
    },
    Game.ZZZ: {
        'asia': 'prod_gf_jp',
        'usa': 'prod_gf_us',
        'euro': 'prod_gf_eu',
        'tw': 'prod_gf_sg',
    },
}

# ==================== (src/config.py) API URLs, ORIGINS, SETTINGS ====================
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

# ==================== SETTINGS ====================
SEMAPHORE_LIMIT = 20
REDEEM_DELAY = 5
REQUEST_TIMEOUT = 30
CONNECT_TIMEOUT = 10
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 5
MIN_UID_LENGTH = 6
DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"  # IANA standard (Asia/Saigon is deprecated)
HEADER_WIDTH = 50              # Số ký tự "=" cho header/footer (main.print_header)

# RPC header values (single source cho checkin, redeem, helpers)
RPC_LANGUAGE = "en-us"
RPC_CLIENT_TYPE = "4"
RPC_PLATFORM = "4"
RPC_SYS_VERSION = "Windows NT 10.0"
RPC_SHOW_TRANSLATED = "false"
PAGE_NAME_HOME_GAME = "HomeGamePage"
PAGE_NAME_HOME = "HomePage"
REDEEM_LANG = "en"
REDEEM_SKIP_MESSAGE_EXPIRED = "⏭ Đã skip (expired/invalid từ region trước)"
COOKIE_CHECK_PAGE_INFO = json.dumps({...}, separators=JSON_SEPARATORS)  # pageName: PAGE_NAME_HOME
COOKIE_CHECK_APP_VERSION = _get_cookie_check_app_version()  # từ env
REDEEM_MESSAGES = {...}
SKIP_REMAINING_IN_REGION = {-2011}
SKIP_GLOBALLY_RETCODES = {-2016, -2001}
SKIP_REMAINING_RETCODES = ...
```

**Cách sử dụng:**
```python
from config import Game, URLS, REGIONS, SEMAPHORE_LIMIT

# Duyệt qua tất cả games
for game in Game:
    print(game.value.name)  # Genshin Impact, Honkai: Star Rail, ...

# Truy cập thông tin game (IDE autocomplete!)
game = Game.GENSHIN
print(game.value.name)      # 'Genshin Impact'
print(game.value.game_id)   # '2'
print(game.value.act_id)    # 'e202102251931481'

# Lấy regions cho game
regions = REGIONS[Game.STAR_RAIL]
print(regions['asia'])       # 'prod_official_asia'

# Lấy URL (vẫn dùng game code)
url = URLS['checkin_sign'][game.value.code]  # gs, sr, zzz
```

**Lợi ích Enum:**
- ✅ IDE autocomplete: `Game.` → hiện GENSHIN, STAR_RAIL, ZZZ
- ✅ Không thể typo: `Game.GENSHIN` (có lỗi ngay) vs `'gs'` (runtime error)
- ✅ Dễ duyệt: `for game in Game:`
- ✅ Type-safe: function nhận `game: Game` không nhận string

---

## 10. Dependencies

```txt
aiohttp>=3.13.3        # Async HTTP client
fake-useragent>=2.2.0 # Dynamic User-Agent headers
```

### 10.1. Lấy biến môi trường (không cần thư viện)

```python
import os

def get_accounts_from_env() -> dict[str, str]:
    """Lấy tất cả biến môi trường bắt đầu bằng ACC_"""
    return {k: v for k, v in os.environ.items() if k.startswith('ACC_') and v.strip()}
```

### 10.2. Tại sao dùng `aiohttp` thay vì `requests`?

| Tiêu chí | `requests` | `aiohttp` |
|----------|-----------|----------|
| **Kiểu** | Synchronous (blocking) | Asynchronous (non-blocking) |
| **Đa luồng** | Cần dùng `threading` hoặc `concurrent.futures` | Native async với `asyncio` |
| **Performance** | Mỗi request block thread | Hàng trăm requests chạy concurrent trên 1 thread |
| **Memory** | Tốn nhiều memory khi spawn threads | Ít memory hơn với event loop |
| **Phù hợp** | Scripts đơn giản, ít requests | Cần gọi nhiều APIs song song |

**Trong project này:**
- Check-in: N accounts × 3 games = queries song song
- Fetch UIDs: N accounts × 3 games × 4 regions = queries song song
- Redeem: Nhiều accounts/servers chạy song song

→ `aiohttp` phù hợp hơn vì cần **concurrency cao** với **ít resources**.

### 10.3. Connection Pooling & Session Reuse

**Vấn đề:** Mỗi request tạo TCP connection mới → tốn thời gian handshake, tốn memory.

**Giải pháp:** Dùng `aiohttp.ClientSession` với connection pool - reuse connections cho nhiều requests.

```python
import aiohttp
import asyncio

async def main():
    # Tạo session 1 lần, dùng cho tất cả requests
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(
            limit=30,          # Max 30 concurrent connections
            limit_per_host=10, # Max 10 connections per host
        ),
        cookie_jar=aiohttp.DummyCookieJar(), # BẮT BUỘC: Cô lập cookie giữa các accounts
        timeout=aiohttp.ClientTimeout(
            total=30,     # Timeout tổng 30s
            connect=10,   # Timeout kết nối 10s
        )
    ) as session:
        # Truyền session vào các hàm
        await run_checkin(session, accounts)
        await run_redeem(session, accounts, cdkeys)

# Ví dụ sử dụng session trong hàm
async def fetch_uid(session: aiohttp.ClientSession, account: Account, game: str, region: str):
    headers = {
        "Cookie": account.cookie_str,
        "x-rpc-device_id": account.mhy_uuid,
        # ... other headers
    }
    async with session.get(URL, headers=headers, params=params) as response:
        return await response.json()
```

**Cách hoạt động:**

```
┌─────────────────────────────────────────────────────────────┐
│  KHÔNG có Connection Pool                                   │
│                                                             │
│  Request 1 → [TCP Handshake] → [Send] → [Receive] → [Close] │
│  Request 2 → [TCP Handshake] → [Send] → [Receive] → [Close] │
│  Request 3 → [TCP Handshake] → [Send] → [Receive] → [Close] │
│                                                             │
│  → Mỗi request tốn ~100ms cho TCP handshake                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  CÓ Connection Pool (aiohttp.ClientSession)                 │
│                                                             │
│  [TCP Handshake lần đầu]                                    │
│       ↓                                                     │
│  Request 1 → [Send] → [Receive] ─┐                          │
│  Request 2 → [Send] → [Receive] ─┼─ Reuse connection        │
│  Request 3 → [Send] → [Receive] ─┘                          │
│                                                             │
│  → Chỉ handshake 1 lần, tiết kiệm ~100ms × (N-1) requests   │
└─────────────────────────────────────────────────────────────┘
```

**Lợi ích:**
- ✅ Reuse TCP connections → nhanh hơn
- ✅ Giảm memory footprint
- ✅ Tự động quản lý connection lifecycle
- ✅ Built-in timeout handling


---

## 13. Chiến lược Repository

### Public Repository để tận dụng GitHub Actions miễn phí

| Loại repo | GitHub Actions |
|-----------|----------------|
| **Public** | ✅ **Miễn phí không giới hạn** |
| Private | ⚠️ 2,000 phút/tháng (Free tier) |

**Cách triển khai an toàn với public repo:**

1. **Cookies lưu trong Secrets** → Không bao giờ lộ trong code
2. **Không log sensitive data** → Mask emails, UIDs trong output
3. **Code không chứa thông tin cá nhân** → Chỉ có logic xử lý

```
┌─────────────────────────────────────────────────────────────┐
│  PUBLIC REPO (ai cũng thấy code)                            │
│  ├── src/                    ← Logic code (OK)             │
│  ├── .github/workflows/      ← Workflow config (OK)         │
│  └── requirements.txt        ← Dependencies (OK)            │
├─────────────────────────────────────────────────────────────┤
│  SECRETS (chỉ owner thấy, encrypted)                        │
│  ├── ACC_1                   ← Cookie account 1             │
│  ├── ACC_2                   ← Cookie account 2             │
│  └── ...                                                    │
└─────────────────────────────────────────────────────────────┘
```

> [!CAUTION]
> Dù là public repo, **TUYỆT ĐỐI** không commit file chứa cookies hoặc hardcode secrets vào code!
---

