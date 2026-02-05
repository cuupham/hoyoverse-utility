# HoYoLab Auto Check-in & Redeem Code Tool

> **Mục tiêu:** Tự động điểm danh hàng ngày và nhập redeem code cho 3 game Hoyoverse: **Genshin Impact**, **Honkai: Star Rail**, **ZZZ** thông qua GitHub Actions.

---

## 1. Tổng quan hệ thống

### 1.1. Games được hỗ trợ

| Game              | Code  |
|-------------------|-------|
| Genshin Impact    | `gs`  |
| Honkai: Star Rail | `sr`  |
| Zenless Zone Zero | `zzz` |

> [!NOTE]
> Chi tiết đầy đủ về Game ID, Act ID, Game Biz xem tại [Section 9.2 - Centralized Config](#92-centralized-config---gom-tất-cả-constants)

### 1.2. Servers/Regions

| Region | Code |
|--------|------|
| Asia   | `asia` |
| USA    | `usa` |
| Europe | `euro` |
| TW/HK  | `tw` |

> [!NOTE]
> Chi tiết region codes theo từng game xem tại [Section 9.2 - REGIONS dict](#92-centralized-config---gom-tất-cả-constants)

### 1.3. Quy tắc nghiệp vụ

- **Điểm danh (Check-in):** Không phân biệt server, chỉ cần account có chơi game đó
- **Nhập redeem code:** Phân biệt theo game + server (cần UID tương ứng)
- **Số lượng code mỗi live stream:**
  - Genshin: 3 codes
  - Star Rail: 3 codes  
  - ZZZ: 1 code
- **Rate limit:** Delay **5 giây** giữa mỗi lần nhập code (cùng account, cùng server)

---

## 2. Cấu hình GitHub Actions

### 2.1. Secrets

Mỗi account Hoyoverse được lưu dưới dạng cookie string trong GitHub Secrets:

```yaml
secrets:
  ACC_1: "<cookie_string_1>"
  ACC_2: "<cookie_string_2>"
  ACC_3: "<cookie_string_3>"
  ACC_4: "<cookie_string_4>"
```

### 2.2. Workflow Environment Variables

```yaml
env:
  ACC_1: ${{ secrets.ACC_1 }}
  ACC_2: ${{ secrets.ACC_2 }}
  ACC_3: ${{ secrets.ACC_3 }}
  ACC_4: ${{ secrets.ACC_4 }}
```

**Biến tùy chọn:**
- `COOKIE_CHECK_APP_VERSION`: Giá trị header `x-rpc-app_version` cho API kiểm tra cookie (user_brief_info). Nếu không set thì gửi rỗng — API vẫn chấp nhận. Khi có phương pháp lấy version (vd iTunes API, xem Roadmap) có thể set biến này.

### 2.3. Cookie Format

```
mi18nLang=en-us; _HYVUUID=xxx; _MHYUUID=xxx; cookie_token_v2=xxx; account_mid_v2=xxx; account_id_v2=xxx; ltoken_v2=xxx; ltmid_v2=xxx; ltuid_v2=xxx; ...
```

**Các giá trị quan trọng cần trích xuất từ cookie:**
- `_MHYUUID` → Dùng cho header `x-rpc-device_id`
- `_HYVUUID` → Dùng cho một số API sign

### 2.4. Account Data Model

Cookie được lưu dưới dạng string trong secrets, nhưng cần parse ra để truy xuất các giá trị riêng lẻ.

**Giải pháp: Dùng dataclass giữ cả 2 dạng**

```python
from dataclasses import dataclass

# Required keys để đảm bảo cookie hoạt động
REQUIRED_COOKIE_KEYS = ['_MHYUUID', '_HYVUUID', 'cookie_token_v2', 'account_id_v2']

@dataclass(frozen=True)  # Immutable - không thể thay đổi sau khi tạo
class Account:
    name: str                    # "ACC_1", "ACC_2", ...
    cookie_str: str              # Raw cookie string cho HTTP requests
    cookies: dict[str, str]      # Parsed dict để truy xuất values
    
    @classmethod
    def from_env(cls, name: str, cookie_str: str) -> "Account":
        """Parse cookie string thành Account object
        
        Raises:
            ValueError: Nếu cookie rỗng hoặc thiếu required keys
        """
        # Kiểm tra cookie rỗng
        if not cookie_str or not cookie_str.strip():
            raise ValueError(f"{name}: Cookie string is empty")
        
        # Parse cookie string
        cookies: dict[str, str] = {}
        for pair in cookie_str.split(';'):
            pair = pair.strip()
            if '=' in pair:
                key, value = pair.split('=', 1)
                cookies[key.strip()] = value.strip()
        
        # Kiểm tra required keys
        missing = [k for k in REQUIRED_COOKIE_KEYS if k not in cookies]
        if missing:
            raise ValueError(f"{name}: Missing required cookies: {missing}")
        
        return cls(name=name, cookie_str=cookie_str, cookies=cookies)
    
    @property
    def mhy_uuid(self) -> str:
        """Trả về _MHYUUID cho x-rpc-device_id"""
        return self.cookies.get('_MHYUUID', '')
    
    @property
    def hyv_uuid(self) -> str:
        """Trả về _HYVUUID cho một số API sign"""
        return self.cookies.get('_HYVUUID', '')
```

> [!NOTE]
> **frozen=True** nghĩa là Account không thể thay đổi sau khi tạo:
> - ✅ Thread-safe
> - ✅ Có thể dùng làm dict key
> - ✅ Tránh bug do vô tình sửa data

**Cách sử dụng:**

```python
# Khởi tạo từ environment variable
acc = Account.from_env("ACC_1", os.environ["ACC_1"])

# Dùng cho HTTP request
headers = {
    "Cookie": acc.cookie_str,       # Raw string
    "x-rpc-device_id": acc.mhy_uuid,  # Parsed value
}

# Truy cập bất kỳ giá trị nào
ltuid = acc.cookies.get("ltuid_v2")
```

---

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
from utils.headers import DYNAMIC_HEADERS

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

## 5. Chi tiết API

### 5.1. API Kiểm tra Cookie hợp lệ

**Mục đích:** Kiểm tra cookie còn sử dụng được hay không

| Property | Value |
|----------|-------|
| URL      | `https://bbs-api-os.hoyolab.com/community/misc/wapi/account/user_brief_info` |
| Method   | `GET` |
| Cookie   | Required |

**Headers:** (theo curl thực tế từ www.hoyolab.com — origin/referer = www, device_id = _HYVUUID, source_info = HomeUserPage/Post)
```python
headers = {
    **COMMON_HEADERS,
    **ORIGINS["hoyolab"],  # origin: https://www.hoyolab.com, referer: https://www.hoyolab.com/
    "Cookie": account.cookie_str,
    "x-rpc-app_version": COOKIE_CHECK_APP_VERSION,  # Từ env COOKIE_CHECK_APP_VERSION; không set thì rỗng
    "x-rpc-client_type": "4",
    "x-rpc-device_id": account.hyv_uuid,           # _HYVUUID (khác với các API khác dùng _MHYUUID)
    "x-rpc-hour": current_hour(),
    "x-rpc-language": "en-us",
    "x-rpc-lrsag": "",
    "x-rpc-page_info": '{"pageName":"HomePage","pageType":"","pageId":"","pageArrangement":"","gameId":""}',  # account-wide, không gắn game
    "x-rpc-page_name": "HomePage",
    "x-rpc-show-translated": "false",
    "x-rpc-source_info": json.dumps({
        "sourceName": "HomeUserPage",
        "sourceType": "Post",
        "sourceId": account.cookies.get("account_id_v2", ""),
        "sourceArrangement": "",
        "sourceGameId": "",
    }, separators=(",", ":")),
    "x-rpc-sys_version": "Windows NT 10.0",
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
params = {
    "lang": "en-us",
    "act_id": ACT_ID  # theo game
}
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

**Headers (Genshin):**
```python
headers = {
    **COMMON_HEADERS,
    **ORIGINS["act_hoyolab"],
    "content-type": "application/json;charset=UTF-8",
    "x-rpc-app_version": "",
    "x-rpc-device_id": cookies["_HYVUUID"],
    "x-rpc-device_name": "",
    "x-rpc-lrsag": "",
    "x-rpc-platform": "4",
}
```

**Headers (Star Rail / ZZZ):**
```python
headers = {
    **COMMON_HEADERS,
    **ORIGINS["act_hoyolab"],
    "x-rpc-client_type": "4",   # Web (đồng bộ với cookie)
    "x-rpc-platform": "4",      # Web/PC
    "x-rpc-signgame": "hkrpg",  # hoặc "zzz"
}
```

**Body:**
```python
# Genshin
json_data = {"act_id": ACT_ID}

# Star Rail / ZZZ
json_data = {"act_id": ACT_ID, "lang": "en-us"}
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

**Headers:**
```python
headers = {
    **COMMON_HEADERS,
    **ORIGINS["act_hoyolab"],
    "x-rpc-client_type": "4",
    "x-rpc-device_id": cookies["_MHYUUID"],
    "x-rpc-hour": current_hour(),
    "x-rpc-language": "en-us",
    "x-rpc-lrsag": "",
    "x-rpc-page_info": game_info.get_page_info(""),
    "x-rpc-page_name": "",
    "x-rpc-show-translated": "false",
    "x-rpc-source_info": '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
    "x-rpc-sys_version": "Windows NT 10.0",
    "x-rpc-timezone": DEFAULT_TIMEZONE,
    "x-rpc-weekday": rpc_weekday(),
}
```

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

**Headers:**
```python
headers = {
    **COMMON_HEADERS,
    **ORIGINS["hoyolab"],
    "x-rpc-client_type": "4",
    "x-rpc-device_id": cookies["_MHYUUID"],
    "x-rpc-hour": current_hour(),
    "x-rpc-language": "en-us",
    "x-rpc-lrsag": "",
    "x-rpc-page_info": game_info.get_page_info("HomeGamePage"),
    "x-rpc-page_name": "HomeGamePage",
    "x-rpc-show-translated": "false",
    "x-rpc-source_info": '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
    "x-rpc-sys_version": "Windows NT 10.0",
    "x-rpc-timezone": DEFAULT_TIMEZONE,
    "x-rpc-weekday": rpc_weekday(),
}
```

**Params:**
```python
params = {
    "region": REGION,     # vd: "os_asia"
    "game_biz": GAME_BIZ  # vd: "hk4e_global"
}
```

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

**Headers:**
```python
headers = {
    **COMMON_HEADERS,
    **ORIGINS["hoyolab"],
    "x-rpc-client_type": "4",
    "x-rpc-device_id": cookies["_MHYUUID"],
    "x-rpc-hour": current_hour(),
    "x-rpc-language": "en-us",
    "x-rpc-lrsag": "",
    "x-rpc-page_info": game_info.get_page_info("HomeGamePage"),
    "x-rpc-page_name": "HomeGamePage",
    "x-rpc-show-translated": "false",
    "x-rpc-source_info": '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
    "x-rpc-sys_version": "Windows NT 10.0",
    "x-rpc-timezone": DEFAULT_TIMEZONE,
    "x-rpc-weekday": rpc_weekday(),
}
```

**Params:**
```python
params = {
    "cdkey": cdkey,
    "game_biz": GAME_BIZ,
    "lang": "en",
    "region": REGION,
    "t": unix_ms(),
    "uid": uid
}
```

> ⚠️ **Quan trọng:** Phải delay **5 giây** giữa mỗi lần nhập code (cùng account, cùng server)

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
    CODE2: ⏭ Skip (đã biết expired từ Asia) → TIẾT KIỆM API call!
  
  Region Europe:
    CODE1: ✓ Thành công
    CODE2: ⏭ Skip (đã biết expired từ Asia)
```

---

## 7. Output Format (Console)

```
============================================================
                    HOYOLAB AUTO TOOL
                    20/01/2026 07:50:58
                    Trace: a83cd482
============================================================

--- KIỂM TRA ACCOUNTS ---
[✓] ACC_1: Hợp lệ (c****u9991@gmail.com)
[✓] ACC_2: Hợp lệ (c****00001@gmail.com)
[✓] ACC_3: Hợp lệ (p****66720@nrlord.com)
[✓] ACC_4: Hợp lệ (n****uck15@gmail.com)

Tổng: 4/4 accounts hợp lệ

--- CHECK-IN ---

=== ACC_1 ===
  Genshin Impact: ✗ No in-game character detected, create one first
  Honkai: Star Rail: ✓ Đã điểm danh trước đó
  Zenless Zone Zero: ✓ Đã điểm danh trước đó

=== ACC_2 ===
  Genshin Impact: ✓ Đã điểm danh trước đó
  Honkai: Star Rail: ✓ Đã điểm danh trước đó
  Zenless Zone Zero: ✓ Đã điểm danh trước đó

--- REDEEM CODE ---

>> Fetching CDKeys...
[SYSTEM] Genshin Impact: Không có codes
[SYSTEM] Honkai: Star Rail: Không có codes
[SYSTEM] Zenless Zone Zero: Không có codes

[SYSTEM] Không có codes nào để redeem
============================================================
DONE - 1.0s
============================================================
```

### 7.1. Chiến lược Centrailized Logging (Gom log)

Để tối ưu hiệu năng (chạy song song) mà vẫn giữ log dễ đọc, tool áp dụng chiến lược:

1.  **API functions:** Chỉ thực thi logic và `return` kết quả dưới dạng dictionary. Không gọi các hàm in log.
2.  **Display functions:** Các hàm `display_checkin()` và `display_redeem()` trong `main.py` nhận kết quả thô và định dạng chúng thành các block log đẹp mắt.

**Lợi ích:**
- Không bị xen kẽ (interleave) log khi nhiều account chạy cùng lúc.
- Tốc độ xử lý song song nhưng hiển thị tuần tự cho con người dễ đọc.

### 7.2. Dual Output Mode (LOG_LEVEL)

Hỗ trợ 2 format output thông qua environment variable `LOG_LEVEL`:

| Mode | Mô tả |
|------|-------|
| `human` | Human-readable (default) |
| `json` | Machine-parseable JSON |
| `both` | Cả 2 format |

```python
# src/utils/logger.py
import os
import json
from enum import Enum
from datetime import datetime

class OutputMode(Enum):
    HUMAN = "human"
    JSON = "json"
    BOTH = "both"

def get_output_mode() -> OutputMode:
    """Get output mode với fallback an toàn"""
    mode = os.environ.get("LOG_LEVEL", "human").lower()
    try:
        return OutputMode(mode)
    except ValueError:
        return OutputMode.HUMAN  # Fallback nếu value không hợp lệ

OUTPUT_MODE = get_output_mode()

# Note: logging.basicConfig được gọi trong ExecutionContext._setup_logging()
# Không gọi ở đây để tránh duplicate

def log_result(data: dict, human_msg: str) -> None:
    """Output theo OUTPUT_MODE setting"""
    if OUTPUT_MODE in (OutputMode.HUMAN, OutputMode.BOTH):
        logger.info(human_msg)
    
    if OUTPUT_MODE in (OutputMode.JSON, OutputMode.BOTH):
        # JSON output vẫn dùng print để không bị format của logging
        print(json.dumps({
            **data,
            "trace_id": ctx.trace_id,
            "timestamp": datetime.now().isoformat(),
        }))

# Note: logger và ctx được import từ phần còn lại của logger.py (Section 8.6)
```

**Ví dụ sử dụng:**
```python
log_result(
    data={"action": "checkin", "game": "gs", "account": "ACC_1", "status": "success", "day": 15},
    human_msg="  Genshin:    ✓ Điểm danh thành công (Ngày 15)"
)
```

**Output theo mode:**
```bash
# LOG_LEVEL=human (default)
20/01/2026 07:50:59 [INFO]   Genshin Impact: ✓ Đã điểm danh trước đó

# LOG_LEVEL=json
{"action":"checkin","game":"gs","account":"ACC_2","status":"success","trace_id":"a83cd482","timestamp":"2026-01-20T07:50:59.123"}
```

**GitHub Actions workflow:**
```yaml
- name: Run script (JSON logs)
  env:
    LOG_LEVEL: json  # hoặc "both" để debug
    ACC_1: ${{ secrets.ACC_1 }}
  run: python -m src.main
```

---

## 8. Error Handling

### 8.1. Các lỗi cần xử lý

| Tình huống | Hành động |
|------------|-----------|
| Không có account nào trong env | In lỗi & THOÁT |
| Tất cả cookies đều invalid | In lỗi & THOÁT |
| Không fetch được CDKey nào | In thông báo & bỏ qua phần redeem |
| Account không có UID nào | Bỏ qua account đó trong phần redeem |
| **TẤT CẢ accounts đều không có UID** | In lỗi & THOÁT (xem bên dưới) |
| API trả về retcode != 0 | Log lỗi và tiếp tục (không crash) |

> [!CAUTION]
> **Trường hợp đặc biệt - Tất cả accounts không có UID:**
> 
> Ví dụ: Có 4 cookies, duyệt qua 3 games × 4 servers = 48 requests nhưng **không lấy được UID nào**.
> 
> Điều này có nghĩa tất cả tài khoản chỉ là Hoyolab account mà chưa bao giờ vào game lần đầu (chưa generate UID).
> 
> → Dù có CDKeys cũng **vô nghĩa** vì muốn nhập code cần có UID + Region tương ứng.
> 
> → **In lỗi rõ ràng và THOÁT chương trình.**

### 8.2. Response Codes thường gặp

| `retcode` | Ý nghĩa | Hành động |
|---------|---------|----------|
| `0` | Thành công | ✅ Tiếp tục |
| `-1` | Lỗi chung | ⚠️ Log và tiếp tục |
| `-100` | Cookie không hợp lệ | ❌ Bỏ qua account |
| `-2001` | Code không tồn tại | ⏭ Skip code ở tất cả regions |
| `-2003` | Code đã được sử dụng | ⚠️ Log và tiếp tục |
| `-2011` | Chưa đủ rank/level | ⏭ Skip các codes còn lại trong region |
| `-2016` | Code đã hết hạn | ⏭ Skip code ở tất cả regions |
| `-2017` | Đã sử dụng hoặc không đủ điều kiện (Level/Rank) | ⚠️ Log và tiếp tục |

> [!TIP]
> **Thứ tự ưu tiên tin nhắn lỗi:** 
> Luôn hiển thị thông báo trả về trực tiếp từ API HoYoLab (`data.message`) trước. Chỉ khi server không gửi thông báo mới sử dụng bảng dịch dự phòng trên.


### 8.4. Exception Handling Pattern với Retry

```python
# src/api/client.py
"""HTTP Client - Retry logic, semaphore, và error handling

SECURITY WARNING: Never log cookies or sensitive headers.
"""

def _sanitize_error_message(error: Exception) -> str:
    """Sanitize error message để không leak sensitive info"""
    error_str = str(error)
    sensitive_patterns = ["cookie", "token", "password", "secret", "key", "auth"]
    
    for pattern in sensitive_patterns:
        if pattern in error_str.lower():
            return "Request failed (details hidden for security)"
    
    return error_str[:100] + "..." if len(error_str) > 100 else error_str


async def safe_api_call(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict,
    params: dict | None = None,
    json_data: dict | None = None,
    method: str = "GET",
    max_retries: int = MAX_RETRIES,
) -> dict[str, Any]:
    """Pattern xử lý exception với retry cho tất cả API calls"""
    kwargs = {"headers": headers}
    if params:
        kwargs["params"] = params
    if json_data:
        kwargs["json"] = json_data
    
    last_error = "Unknown error"
    
    for attempt in range(max_retries):
        try:
            async with _get_semaphore():  # Lazy init semaphore
                async with session.request(method, url, **kwargs) as resp:
                    if resp.status == 429:  # Rate limited
                        await asyncio.sleep(RATE_LIMIT_DELAY)
                        continue
                    data = await resp.json()
                    return {"success": True, "data": data}
        
        except aiohttp.ClientConnectionError:
            last_error = "Network connection failed"
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
        
        except asyncio.TimeoutError:
            last_error = "Request timed out"
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
        
        except aiohttp.ContentTypeError:
            return {"success": False, "error": "invalid_json", "message": "Response not JSON"}
        
        except Exception as e:
            return {"success": False, "error": "unknown", "message": _sanitize_error_message(e)}
    
    return {"success": False, "error": "max_retries", "message": f"Failed after {max_retries} attempts"}
```

### 8.5. Semaphore giới hạn Concurrent Requests

> [!NOTE]
> Semaphore đã được tích hợp trong `safe_api_call` (xem Section 8.4).
> - `SEMAPHORE_LIMIT = 20` concurrent requests max
> - Ví dụ: 48 requests → chỉ 20 chạy cùng lúc, còn lại đợi


### 8.6. Execution Context (Logging Correlation)

Mỗi lần chạy script cần có `trace_id` để dễ debug trong logs:

```python
# src/utils/logger.py
import uuid
import logging
from datetime import datetime
from typing import Any

# Configure logging với custom format
class TraceIdFilter(logging.Filter):
    """Filter thêm trace_id vào mỗi log record"""
    def __init__(self, trace_id: str):
        super().__init__()
        self.trace_id = trace_id
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = self.trace_id
        return True

class ExecutionContext:
    """Singleton chứa context cho 1 lần chạy"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.trace_id = uuid.uuid4().hex[:8]
            cls._instance.start_time = datetime.now()
            cls._instance._setup_logging()
        return cls._instance
    
    def _setup_logging(self) -> None:
        """Setup logging với trace_id filter và force flush"""
        # Tạo custom handler với force flush
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%d/%m/%Y %H:%M:%S"
        ))
        
        # Override emit để force flush sau mỗi log
        original_emit = handler.emit
        def flush_emit(record):
            original_emit(record)
            handler.flush()
        handler.emit = flush_emit
        
        # Cấu hình root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.addFilter(TraceIdFilter(self.trace_id))
    
    @property
    def elapsed_seconds(self) -> float:
        """Thời gian đã chạy (giây)"""
        return (datetime.now() - self.start_time).total_seconds()

# Global instance - khởi tạo khi import
ctx = ExecutionContext()
logger = logging.getLogger(__name__)

def log_info(account: str, message: str) -> None:
    """Log level INFO"""
    logger.info(f"[{account}] {message}")

def log_error(account: str, message: str) -> None:
    """Log level ERROR"""
    logger.error(f"[{account}] {message}")

def log_warning(account: str, message: str) -> None:
    """Log level WARNING"""
    logger.warning(f"[{account}] {message}")

def log_debug(account: str, message: str) -> None:
    """Log level DEBUG - chỉ hiển khi LOG_LEVEL=DEBUG"""
    logger.debug(f"[{account}] {message}")
```

**Output example:**
```
20/01/2026 07:50:59 [INFO] [ACC_1] Check-in Zenless Zone Zero: ✓ Đã điểm danh trước đó
20/01/2026 07:50:59 [ERROR] [ACC_2] Cookie expired
```

**Lợi ích:**
- Tất cả logs cùng execution có chung `trace_id`
- Dễ filter logs theo execution run trong GitHub Actions
- Dễ tính execution time (từ `start_time`)

### 8.7. Decoupled Display Pattern

Khi phát triển luồng mới, tuân thủ nguyên tắc:
1. Hàm thực thi (API/Service) trả về `dict` hoặc `list`.
2. Hàm hiển thị (Display) nhận dữ liệu đó và dùng `log_print()` để in ra.

```python
# Ví dụ pattern chuẩn trong main.py
results = await run_something_parallel(accounts)
display_something(results)  # In ra tuần tự
```

---

## 9. Project Structure (Đề xuất)

```
hoyolab-auto/
├── .github/
│   └── workflows/
│       └── hoyo-flow.yml       # GitHub Actions workflow
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── config.py               # Constants & configurations
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py           # HTTP client wrapper (retry, semaphore)
│   │   ├── checkin.py          # Check-in APIs
│   │   └── redeem.py           # Redeem code APIs
│   ├── models/
│   │   ├── __init__.py
│   │   ├── account.py          # Account model
│   │   └── game.py             # Game & Region models
│   └── utils/
│       ├── __init__.py
│       ├── headers.py          # Dynamic User-Agent headers
│       ├── helpers.py          # Helper functions
│       ├── logger.py           # Logging utilities
│       └── security.py         # Mask sensitive data
├── tests/                      # Unit tests & Mocks
│   ├── conftest.py
│   ├── test_checkin.py
│   ├── test_redeem.py
│   ├── test_core.py
│   └── cookies.ps1.example
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

Tất cả constants được gom vào 1 file `config.py` để dễ quản lý và sửa đổi khi API thay đổi.

```python
# src/config.py

# ==================== GAMES (Enum) ====================
from enum import Enum
from dataclasses import dataclass

@dataclass(frozen=True)
class GameInfo:
    """Thông tin của 1 game"""
    code: str              # 'gs', 'sr', 'zzz'
    name: str              # Tên hiển thị
    game_id: str           # ID dùng trong API
    act_id: str            # Act ID cho check-in
    game_biz: str           # Game biz string
    signgame: str | None   # Signgame header (None cho Genshin)
    page_type: str = ""    # Type trang cụ thể (vd: ZZZ=46)

    def get_page_info(self, page_name: str = "HomeGamePage") -> str:
        """Sinh chuỗi JSON cho x-rpc-page_info với game_id và page_type động"""
        import json
        return json.dumps({
            "pageName": page_name,
            "pageType": self.page_type,
            "pageId": "",
            "pageArrangement": "Hot" if page_name == "HomeGamePage" else "",
            "gameId": self.game_id
        }, separators=(',', ':'))

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
SEMAPHORE_LIMIT = 20      # Max concurrent requests
REDEEM_DELAY = 5          # Seconds between redeem codes
REQUEST_TIMEOUT = 30      # Total request timeout
CONNECT_TIMEOUT = 10      # Connection timeout
MAX_RETRIES = 3           # Retry attempts
RATE_LIMIT_DELAY = 5      # Seconds to wait when rate limited (429)
MIN_UID_LENGTH = 6        # UIDs shorter than this are masked entirely

# Cookie check (user_brief_info): x-rpc-app_version
# Đọc từ env COOKIE_CHECK_APP_VERSION; không set thì gửi rỗng (API vẫn chấp nhận).
# Khi có phương pháp lấy version (vd iTunes API) có thể set env hoặc cập nhật config.
def _get_cookie_check_app_version() -> str:
    v = os.environ.get("COOKIE_CHECK_APP_VERSION", "").strip()
    return v if v else ""
COOKIE_CHECK_APP_VERSION = _get_cookie_check_app_version()
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

## 11. GitHub Actions Workflow (Đề xuất)

```yaml
name: HoYoLab Daily Check-in & Redeem

on:
  schedule:
    # 4:45 sáng giờ Việt Nam (GMT+7) = 21:45 UTC ngày hôm trước
    - cron: '45 21 * * *'
  workflow_dispatch:  # Cho phép chạy manual

jobs:
  run:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Set up Python with pip cache
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'  # Built-in cache, tự detect requirements.txt
          
      - name: Install dependencies
        run: pip install -r requirements.txt
        
      - name: Run script
        env:
          ACC_1: ${{ secrets.ACC_1 }}
          ACC_2: ${{ secrets.ACC_2 }}
          ACC_3: ${{ secrets.ACC_3 }}
          ACC_4: ${{ secrets.ACC_4 }}
        run: python -m src.main
```

> [!TIP]
> **Tại sao chạy lúc 4:45 sáng VN?**
> - Server Hoyoverse reset daily rewards vào 4:00 AM theo timezone của server
> - Chạy lúc 4:45 đảm bảo đã qua thời điểm reset
> - Tránh rush hour của các tool tự động khác (thường chạy đúng 4:00 hoặc 5:00)

---

## 12. Lưu ý quan trọng

> [!IMPORTANT]
> - Cookies có thể hết hạn sau một thời gian, cần update lại trong GitHub Secrets
> - Delay 5s giữa các lần nhập code là BẮT BUỘC để tránh bị rate limit
> - API có thể thay đổi bất cứ lúc nào từ phía Hoyoverse

> [!WARNING]
> - KHÔNG commit cookies lên git repository
> - KHÔNG share cookies với người khác
> - Tool này chỉ dành cho mục đích cá nhân

> [!NOTE]
> - Genshin và Star Rail thường có 3 codes mỗi live stream (6 tuần/lần)
> - ZZZ thường chỉ có 1 code
> - Codes thường hết hạn sau 12-24 giờ từ lúc công bố

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

## 14. Testing

Project sử dụng `pytest` kết hợp với `pytest-asyncio` để kiểm tra toàn bộ logic nghiệp vụ mà không cần gọi API thực tế (Mocking).

### 14.1. Cấu trúc Testing

```
tests/
├── conftest.py          # Fixtures & Mock data chung
├── test_checkin.py      # Test logic điểm danh (Sol/Luna)
├── test_redeem.py       # Test logic đổi code & cross-region skip
├── test_core.py         # Test models, utils và session isolation
└── cookies.ps1.example  # Template hướng dẫn set cookies local
```

### 14.2. Các kịch bản Test quan trọng

- **Session Isolation**: Đảm bảo `ClientSession` dùng `DummyCookieJar` để không bị rò rỉ cookie giữa các tài khoản khi chạy song song.
- **Header Differentiation**: Kiểm tra `x-rpc-*` headers được gửi đúng theo từng loại game (Sol vs Luna).
- **Cross-region Skip**: Xác nhận nếu mã lỗi là `-2001` (hết hạn), tool sẽ tự động skip ở tất cả các region tiếp theo của game đó.
- **Account Validation**: Đảm bảo cookie được parse chính xác và ném lỗi nếu thiếu các key bắt buộc (`_MHYUUID`, `account_id_v2`,...).

### 14.3. Cách chạy Test

```bash
# Cài đặt pytest-asyncio trước
pip install pytest-asyncio

# Chạy toàn bộ test suite
pytest tests
```

---

## 15. Roadmap & Tương lai (Planned)

### 🚀 Smart Version Detection
Tự động săn phiên bản HoYoLab mới nhất từ App Store (iTunes API lookup ID `1559483982`) để thay thế việc set cứng `APP_VERSION`. Điều này giúp bypass các đợt cập nhật app bất ngờ của HoYoverse.

### 🌎 Standardized Local Timezone
Tự động lấy múi giờ hệ thống (Local Timezone) thay vì mặc định `Asia/Saigon`. Đảm bảo tính nhất quán khi người dùng chạy tool ở các khu vực khác nhau trên thế giới.

### 🧹 Clean Logistics Report
Cải thiện hiển thị: Tự động ẩn danh sách các account không có nhân vật/UID hợp lệ trong phần Redeem Code để báo cáo gọn gàng, chuyên nghiệp hơn.
