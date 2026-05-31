# API Contract & Configuration

## 3. API Configuration

### 3.1. Common Headers

> [!TIP]
> Sử dụng `fake-useragent` để tự động lấy User-Agent mới nhất, tránh hardcode bị outdated.

```python
# src/utils/headers.py
import re
from fake_useragent import UserAgent

def get_dynamic_headers() -> dict[str, str]:
    """Generate headers với User-Agent Chrome mới nhất"""
    ua = UserAgent()
    chrome_ua = ua.chrome
    
    # Parse version từ UA string: "Chrome/143.0.0.0" → "143"
    match = re.search(r'Chrome/(\d+)', chrome_ua)
    version = match.group(1) if match else "142"
    
    return {
        "user-agent": chrome_ua,
        "sec-ch-ua": f'"Chromium";v="{version}", "Google Chrome";v="{version}", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

# Gọi 1 lần khi khởi động
DYNAMIC_HEADERS = get_dynamic_headers()
```

```python
# src/config.py
from src.utils.headers import DYNAMIC_HEADERS

COMMON_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9,vi-VN;q=0.8,vi;q=0.7",
    **DYNAMIC_HEADERS,  # Merge dynamic User-Agent headers
    "dnt": "1",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "priority": "u=1, i", # Header mới để tăng độ stealth
}
```

### 3.2. Origins

> [!NOTE]
> `ORIGINS` dict được định nghĩa tại `src/config.py` (chỉ 2 origins: `hoyolab` và `act_hoyolab`)

### 3.3. Helper Functions (đã implement tại `src/utils/helpers.py`)

```python
from datetime import datetime
import time

def current_hour() -> str:
    """Trả về giờ hiện tại dạng 2 chữ số (00-23)"""
    return f'{datetime.now().hour:02}'

def rpc_weekday() -> str:
    """Trả về thứ trong tuần (1=Monday, 7=Sunday)"""
    return str(datetime.now().isoweekday())

def unix_ms() -> int:
    """Trả về timestamp hiện tại dạng milliseconds"""
    return int(time.time() * 1000)
```

---

## 5. Chi tiết API

### 5.1. API Kiểm tra Cookie hợp lệ

**Mục đích:** Kiểm tra cookie còn sử dụng được hay không

| Property | Value |
|----------|-------|
| URL      | `https://bbs-api-os.hoyolab.com/community/misc/wapi/account/user_brief_info` |
| Method   | `GET` |
| Cookie   | Required |

**Headers:** Dùng `build_rpc_headers(account, "hoyolab", COOKIE_CHECK_PAGE_INFO, PAGE_NAME_HOME, source_info)` với source_info = HomeUserPage/Post. Giá trị RPC lấy từ `config`: `RPC_CLIENT_TYPE`, `RPC_LANGUAGE`, `RPC_SHOW_TRANSLATED`, `RPC_SYS_VERSION`, `PAGE_NAME_HOME`, `COOKIE_CHECK_PAGE_INFO`; source_info dùng `constants.JSON_SEPARATORS`. Không gửi `x-rpc-app_version` (đã verify không cần thiết).
```python
headers = {
    **COMMON_HEADERS,
    **ORIGINS["hoyolab"],
    "Cookie": account.cookie_str,
    "x-rpc-client_type": RPC_CLIENT_TYPE,
    "x-rpc-device_id": account.mhy_uuid,  # _MHYUUID
    "x-rpc-hour": current_hour(),
    "x-rpc-language": RPC_LANGUAGE,
    "x-rpc-lrsag": "",
    "x-rpc-page_info": COOKIE_CHECK_PAGE_INFO,  # account-wide, không gắn game
    "x-rpc-page_name": PAGE_NAME_HOME,
    "x-rpc-show-translated": RPC_SHOW_TRANSLATED,
    "x-rpc-source_info": json.dumps({...}, separators=JSON_SEPARATORS),  # sourceName: HomeUserPage, sourceType: Post
    "x-rpc-sys_version": RPC_SYS_VERSION,
    "x-rpc-timezone": DEFAULT_TIMEZONE,
    "x-rpc-weekday": rpc_weekday(),
}
```

**Response:**
```json
{
  "retcode": 0,
  "message": "OK",
  "data": {
    "email_mask": "u***@gmail.com",
    ...
  }
}
```

**Logic xử lý:**
- ✅ `retcode == 0` VÀ `data.email_mask` có giá trị → Cookie hợp lệ
- ❌ Các trường hợp khác → Cookie không hợp lệ (hết hạn hoặc đổi mật khẩu)

---

### 5.2. API Check-in (Điểm danh)

#### 5.2.1. Kiểm tra đã điểm danh chưa

| Game | URL |
|------|-----|
| Genshin | `https://sg-hk4e-api.hoyolab.com/event/sol/info` |
| Star Rail | `https://sg-public-api.hoyolab.com/event/luna/hkrpg/os/info` |
| ZZZ | `https://sg-public-api.hoyolab.com/event/luna/zzz/os/info` |

**Method:** `GET`

**Headers (Minimal):**
```python
headers = {
    **COMMON_HEADERS,
    **ORIGINS["act_hoyolab"],
    # Chỉ gửi x-rpc header cần thiết cho từng game
    "x-rpc-lrsag": "",          # Cho Genshin (Sol)
    "x-rpc-signgame": "hkrpg",  # Cho Star Rail (Luna)
}
```

**Params:**
```python
params = {"lang": RPC_LANGUAGE, "act_id": game_info.act_id}  # RPC_LANGUAGE từ config
```

**Response:**
```json
{
  "retcode": 0,
  "message": "OK",
  "data": {
    "is_sign": false,
    "total_sign_day": 5,
    ...
  }
}
```

**Logic xử lý:**
- `retcode != 0` → Lỗi, lưu message và kết thúc
- `retcode == 0` và `is_sign == true` → Đã điểm danh, kết thúc
- `retcode == 0` và `is_sign == false` → Chưa điểm danh, gọi API sign

---

#### 5.2.2. Thực hiện điểm danh

| Game | URL |
|------|-----|
| Genshin | `https://sg-hk4e-api.hoyolab.com/event/sol/sign?lang=en-us` |
| Star Rail | `https://sg-public-api.hoyolab.com/event/luna/hkrpg/os/sign` |
| ZZZ | `https://sg-public-api.hoyolab.com/event/luna/zzz/os/sign` |

**Method:** `POST`

**Headers:** Base từ `build_rpc_headers(account, "act_hoyolab", ...)` — gồm `x-rpc-client_type` (`config.RPC_CLIENT_TYPE`), `x-rpc-device_id` (`account.mhy_uuid`), v.v. (xem `get_sign_headers` trong `src/models/game.py`).

**Headers (Genshin riêng):** thêm `content-type: application/json;charset=UTF-8`, `x-rpc-app_version: ""`, `x-rpc-device_name: ""` (quirk bắt buộc của Genshin sign API).

**Headers (Star Rail / ZZZ riêng):** thêm `x-rpc-signgame` = `game_info.signgame` (`hkrpg` / `zzz`).

**Body:**
```python
# Genshin
json_data = {"act_id": game_info.act_id}

# Star Rail / ZZZ
json_data = {"act_id": game_info.act_id, "lang": RPC_LANGUAGE}
```

---

### 5.3. API Fetch CDKeys (Lấy danh sách redeem code) — `src/api/redeem_fetch.py`

**Mục đích:** Lấy danh sách redeem code hiện có của mỗi game

> [!IMPORTANT]
> **CDKeys là PUBLIC** - không phụ thuộc vào account.
>
> → Fetch CDKeys từ **tất cả accounts song song**, chọn kết quả tốt nhất (nhiều codes nhất).
>
> → Chiến lược fallback: nếu account đầu bị lỗi, accounts khác vẫn trả về codes.
>
> → Kết quả được **dùng chung** cho tất cả accounts khi redeem.

```
Flow Fetch CDKeys (with fallback):
┌─────────────────────────────────────────────────────────────┐
│  Accounts: [acc_1, acc_2, acc_3, acc_4]                     │
│                │                                            │
│    ┌───────────┼───────────┼───────────┐                    │
│    ▼           ▼           ▼           ▼                    │
│  [acc_1]     [acc_2]     [acc_3]     [acc_4]                │
│  3 games     3 games     3 games     3 games                │
│    │           │           │           │                    │
│    └───────────┴───────────┴───────────┘                    │
│                │                                            │
│                ▼                                            │
│  Chọn kết quả có nhiều codes nhất                           │
│                │                                            │
│                ▼                                            │
│  cdkeys = { gs: [...], sr: [...], zzz: [...] }              │
│                │                                            │
│                ▼                                            │
│  Dùng chung cho acc_1, acc_2, acc_3, acc_4                  │
└─────────────────────────────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| URL      | `https://bbs-api-os.hoyolab.com/community/painter/wapi/circle/channel/guide/material` |
| Method   | `GET` |

**Headers:** Dùng `build_rpc_headers(account, "act_hoyolab", game_info.get_page_info(""), page_name="")` từ `utils/helpers.py`; default `source_info` lấy từ `constants.DEFAULT_SOURCE_INFO`; các giá trị RPC lấy từ config (RPC_CLIENT_TYPE, RPC_LANGUAGE, RPC_SHOW_TRANSLATED, RPC_SYS_VERSION).

**Params:**
```python
params = {"game_id": GAME_ID}  # 2=Genshin, 6=StarRail, 8=ZZZ
```

**Trích xuất codes từ response:**
```python
codes = [
    bonus["exchange_code"]
    for module in response.get("data", {}).get("modules", [])
    if (group := module.get("exchange_group"))
    for bonus in group.get("bonuses", [])
    if bonus.get("exchange_code")
]
```

---

### 5.4. API Fetch UID (Lấy UID player) — `src/api/redeem_fetch.py`

**Mục đích:** Lấy UID của player cho **mọi** game/server trong **1 request**

| Property | Value |
|----------|-------|
| URL      | `https://api-account-os.hoyolab.com/binding/api/getUserGameRolesByLtoken` |
| Method   | `GET` |

**Headers:** Dùng `build_rpc_headers(account, "hoyolab", ALL_ROLES_PAGE_INFO, page_name=PAGE_NAME_HOME)` — page_info account-wide (gameId rỗng), vì query không gắn game cụ thể.

**Params:** Không có. Gọi endpoint **không kèm** `region`/`game_biz` → API trả về tất cả game roles của account.

**Trích xuất + map ngược UID:**
```python
# response["data"]["list"] chứa mọi role: {game_biz, region, game_uid, ...}
for role in response["data"].get("list", []):
    game = GAME_BY_BIZ.get(role.get("game_biz"))          # "hkrpg_global" -> Game.STAR_RAIL
    if game is None:
        continue                                           # Game không hỗ trợ (Honkai 3rd...)
    region_code = REGION_CODE_BY_VALUE.get((game, role.get("region")))  # "prod_gf_jp" -> "asia"
    uid = role.get("game_uid")
    if region_code and uid:
        uids[game][region_code] = uid
```
`GAME_BY_BIZ` và `REGION_CODE_BY_VALUE` derive từ `Game` enum + `REGIONS` (single source) trong `src/models/game.py`. Dict UID trả về dùng **region code** (asia, usa, euro, tw).

**Chiến lược:**
- **1 request/account** lấy mọi UID (trước đây 3 games × 4 regions = 12 request rỗng dư thừa)
- Roles của game/region không hỗ trợ → bỏ qua khi map ngược
- Accounts không có UID nào (chưa vào game lần nào) sẽ bị bỏ qua ở bước redeem

---

### 5.5. API Exchange CDKey (Nhập redeem code) — `src/api/redeem_exchange.py`

| Game | URL |
|------|-----|
| Genshin | `https://public-operation-hk4e.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl` |
| Star Rail | `https://public-operation-hkrpg.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl` |
| ZZZ | `https://public-operation-nap.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl` |

**Method:** `GET`

**Headers:** Dùng `build_rpc_headers(account, "hoyolab", game_info.get_page_info(PAGE_NAME_HOME_GAME), page_name=PAGE_NAME_HOME_GAME)`.

**Params:**
```python
params = {
    "cdkey": cdkey,
    "game_biz": game_info.game_biz,
    "lang": REDEEM_LANG,  # từ config (khác RPC_LANGUAGE)
    "region": region_value,  # REGIONS[game][region_code]; hàm nhận region_code (asia, usa, euro, tw)
    "t": unix_ms(),
    "uid": uid,
}
```

> ⚠️ **Quan trọng:** Phải delay **5 giây** giữa mỗi lần nhập code (cùng account, cùng server)

---

