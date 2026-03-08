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
> `ORIGINS` dict được định nghĩa tại [Section 9.2 - Centralized Config](#92-centralized-config---gom-tất-cả-constants)

### 3.3. Helper Functions (cần implement)

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

**Headers:** (theo curl thực tế từ www.hoyolab.com — origin/referer = www, device_id = _HYVUUID, source_info = HomeUserPage/Post). Giá trị RPC lấy từ `config`: `RPC_CLIENT_TYPE`, `RPC_LANGUAGE`, `RPC_SHOW_TRANSLATED`, `RPC_SYS_VERSION`, `PAGE_NAME_HOME`, `COOKIE_CHECK_PAGE_INFO`; source_info dùng `constants.JSON_SEPARATORS`.
```python
headers = {
    **COMMON_HEADERS,
    **ORIGINS["hoyolab"],
    "Cookie": account.cookie_str,
    "x-rpc-app_version": COOKIE_CHECK_APP_VERSION,
    "x-rpc-client_type": RPC_CLIENT_TYPE,
    "x-rpc-device_id": account.hyv_uuid,  # _HYVUUID (khác các API khác dùng _MHYUUID)
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

**Headers (Genshin):** `content-type`, `x-rpc-app_version`, `x-rpc-device_id` (account.hyv_uuid), `x-rpc-platform` (từ `config.RPC_PLATFORM`).

**Headers (Star Rail / ZZZ):** `x-rpc-client_type`, `x-rpc-platform` lấy từ `config.RPC_CLIENT_TYPE`, `config.RPC_PLATFORM`; `x-rpc-signgame` = game_info.signgame.

**Body:**
```python
# Genshin
json_data = {"act_id": game_info.act_id}

# Star Rail / ZZZ
json_data = {"act_id": game_info.act_id, "lang": RPC_LANGUAGE}
```

---

### 5.3. API Fetch CDKeys (Lấy danh sách redeem code)

**Mục đích:** Lấy danh sách redeem code hiện có của mỗi game

> [!IMPORTANT]
> **CDKeys là PUBLIC** - không phụ thuộc vào account.
> 
> → Chỉ cần **1 account đầu tiên** trong danh sách gọi 3 API (cho 3 games) để fetch CDKeys.
> 
> → Kết quả này được **cache và dùng chung** cho tất cả accounts còn lại.
> 
> → **KHÔNG cần** mỗi account tự fetch riêng (tốn API calls vô ích).

```
Flow Fetch CDKeys:
┌─────────────────────────────────────────────────────────────┐
│  Accounts: [acc_1, acc_2, acc_3, acc_4]                     │
│                │                                            │
│                ▼                                            │
│  Lấy acc_1 (account đầu tiên)                               │
│                │                                            │
│    ┌───────────┼───────────┐                                │
│    ▼           ▼           ▼                                │
│  [Genshin]  [StarRail]   [ZZZ]   ← 3 luồng song song        │
│    │           │           │                                │
│    └───────────┴───────────┘                                │
│                │                                            │
│                ▼                                            │
│  cdkeys = {                                                 │
│      "gs": ["CODE1", "CODE2", "CODE3"],                     │
│      "sr": ["CODE4", "CODE5", "CODE6"],                     │
│      "zzz": ["CODE7"]                                       │
│  }                                                          │
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

### 5.4. API Fetch UID (Lấy UID player)

**Mục đích:** Lấy UID của player cho từng game/server

| Property | Value |
|----------|-------|
| URL      | `https://api-account-os.hoyolab.com/binding/api/getUserGameRolesByLtoken` |
| Method   | `GET` |

**Headers:** Dùng `build_rpc_headers(account, "hoyolab", game_info.get_page_info(PAGE_NAME_HOME_GAME), page_name=PAGE_NAME_HOME_GAME)`; `PAGE_NAME_HOME_GAME` từ config.

**Params:**
```python
params = {"region": region_value, "game_biz": game_info.game_biz}
```
`region_value` = `REGIONS[game][region_code]`; trong code và dict UID trả về dùng **region code** (asia, usa, euro, tw). Xem `docs/REGIONS-EXPLAINED.md`.

**Trích xuất UID:**
```python
if response["retcode"] == 0:
    uid_list = response["data"].get("list", [])
    if uid_list:  # Kiểm tra list không rỗng
        uid = uid_list[0].get("game_uid")
    else:
        uid = None  # Account chưa chơi game này ở region này
```

**Chiến lược đa luồng:** 
- Mỗi account duyệt 3 games × 4 regions = **12 luồng song song**
- Accounts không có UID nào (chưa vào game lần nào) sẽ bị bỏ qua

---

### 5.5. API Exchange CDKey (Nhập redeem code)

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

