# HoYoLab Auto Check-in & Redeem Code Tool

> **Mục tiêu:** Tự động điểm danh hàng ngày và nhập redeem code cho 3 game Hoyoverse: **Genshin Impact**, **Honkai: Star Rail**, **ZZZ** thông qua GitHub Actions.

---


## 📚 Tài liệu kỹ thuật chi tiết

Dự án đã được phân tách thành các tài liệu nhỏ để dễ tra cứu và bảo trì:
- 📖 [API Contract & Configuration](api_contract.md) - Chi tiết các endpoints, headers, payloads cho Check-in/Redeem.
- 🏗️ [System Architecture & Flows](architecture.md) - Sơ đồ luồng, chiến lược đa luồng (Threading), và cấu trúc thư mục.
- ⚠️ [Error Handling & Codes](error_codes.md) - Output console format, bảng mã lỗi và pattern xử lý ngoại lệ.

## 1. Tổng quan hệ thống

### 1.1. Games được hỗ trợ

| Game              | Code  |
|-------------------|-------|
| Genshin Impact    | `gs`  |
| Honkai: Star Rail | `sr`  |
| Zenless Zone Zero | `zzz` |

> [!NOTE]
> Chi tiết đầy đủ về Game ID, Act ID, Game Biz xem tại `src/models/game.py` (class `GameInfo`)

### 1.2. Servers/Regions

| Region | Code |
|--------|------|
| Asia   | `asia` |
| USA    | `usa` |
| Europe | `euro` |
| TW/HK  | `tw` |

> [!NOTE]
> Chi tiết region codes theo từng game xem tại `src/models/game.py` (dictionary `REGIONS`)

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

Secrets được inject tự động qua `toJSON(secrets)` với heredoc syntax (chống injection):

```yaml
- name: Inject ACC secrets into env
  env:
    ALL_SECRETS: ${{ toJSON(secrets) }}
  run: |
    python3 -c "
    import json, os, uuid
    secrets = json.loads(os.environ['ALL_SECRETS'])
    env_file = os.environ['GITHUB_ENV']
    acc_secrets = {k: v for k, v in secrets.items() if k.startswith('ACC_') and v.strip()}
    with open(env_file, 'a') as f:
        for key, value in sorted(acc_secrets.items()):
            delimiter = f'ghadelim_{uuid.uuid4().hex[:8]}'
            f.write(f'{key}<<{delimiter}\n{value}\n{delimiter}\n')
    "
```

> [!NOTE]
> Chỉ filter `ACC_*` keys — không dump `GITHUB_TOKEN` hay secrets khác vào env.
> Heredoc syntax ngăn cookie chứa `=` hoặc newline inject env vars.

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

## 3. GitHub Actions Workflow (Đề xuất)

```yaml
name: HoYo Flow

on:
  schedule:
    - cron: '45 21 * * *'
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  core_flow:
    runs-on: ubuntu-latest
    environment: live
    timeout-minutes: 30

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Set up Python with pip cache
        uses: actions/setup-python@v6
        with:
          python-version: '3.13'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Inject ACC secrets into env
        env:
          ALL_SECRETS: ${{ toJSON(secrets) }}
        run: |
          # Filter ACC_* keys + heredoc syntax (xem §2.2)
          python3 -c "..."

      - name: Run script
        run: python -m src.main
```

> [!TIP]
> **Tại sao chạy lúc 4:45 sáng VN?**
> - Server Hoyoverse reset daily rewards vào 4:00 AM theo timezone của server
> - Chạy lúc 4:45 đảm bảo đã qua thời điểm reset
> - Tránh rush hour của các tool tự động khác (thường chạy đúng 4:00 hoặc 5:00)

---

## 4. Lưu ý quan trọng

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

## 5. Testing

Project sử dụng `pytest` kết hợp với `pytest-asyncio` để kiểm tra toàn bộ logic nghiệp vụ mà không cần gọi API thực tế (Mocking).

### 5.1. Cấu trúc Testing

```
tests/
├── auth/                  # Các file auth local (cookies.ps1.example)
├── api-health/            # API health check scripts
├── integration/           # End-to-end integration tests (test_integration.py)
├── scripts/               # Script hỗ trợ Debug API (debug_checkin_info.py)
├── unit/                  # Unit tests chi tiết
│   ├── test_checkin.py    # Test logic điểm danh (Sol/Luna)
│   ├── test_core.py       # Test models, utils và session isolation
│   ├── test_coverage_audit.py
│   ├── test_display.py    # Test UI formatting (display module)
│   ├── test_fetch_cdkeys.py
│   ├── test_fetch_uids.py # Test fetch UIDs (game × region)
│   ├── test_main_flow.py  # Test main orchestration flow
│   └── test_redeem.py     # Test đổi code & cross-region skip
├── conftest.py            # Fixtures & Mock data chung
└── pytest.ini             # (root level) Pytest config
```

### 5.2. Các kịch bản Test quan trọng

- **Session Isolation**: Đảm bảo `ClientSession` dùng `DummyCookieJar` để không bị rò rỉ cookie giữa các tài khoản khi chạy song song.
- **Header Differentiation**: Kiểm tra `x-rpc-*` headers được gửi đúng theo từng loại game (Sol vs Luna).
- **Cross-region Skip**: Xác nhận nếu mã lỗi là `-2001` hoặc `-2016` (hết hạn/expired), tool sẽ tự động skip ở tất cả các region tiếp theo của game đó.
- **Account Validation**: Đảm bảo cookie được parse chính xác và ném lỗi nếu thiếu các key bắt buộc (`_MHYUUID`, `_HYVUUID`, `cookie_token_v2`, `account_id_v2`).
- **Display Formatting**: Đảm bảo display functions format đúng kết quả check-in, CDKeys, UIDs và redeem results.
- **Fetch UIDs**: Đảm bảo fetch UIDs song song (game × region) và lọc đúng accounts có UID.
- **Main Flow**: Test orchestration flow end-to-end (validate → check-in → fetch → redeem).

### 5.3. Cách chạy Test

```bash
# Cài đặt test dependencies
pip install pytest pytest-asyncio pytest-cov

# Chạy toàn bộ test suite
python -m pytest

# Chạy với coverage report
python -m pytest --cov=src --cov-report=term-missing

# Chạy chỉ unit tests
python -m pytest tests/unit/

# Chạy tests với live API (cần cookie)
python -m pytest -m live -v
```

> [!NOTE]
> CI pipeline (`test.yml`) chạy tự động trên mỗi push/PR với `--cov-fail-under=95`.

---

## 6. Roadmap & Tương lai (Planned)

### 🚀 Smart Version Detection
Tự động săn phiên bản HoYoLab mới nhất từ App Store (iTunes API lookup ID `1559483982`) để thay thế việc set cứng `APP_VERSION`. Điều này giúp bypass các đợt cập nhật app bất ngờ của HoYoverse.

### 🌎 Standardized Local Timezone
Tự động lấy múi giờ hệ thống (Local Timezone) thay vì mặc định `Asia/Saigon`. Đảm bảo tính nhất quán khi người dùng chạy tool ở các khu vực khác nhau trên thế giới.

### 🧹 Clean Logistics Report
Cải thiện hiển thị: Tự động ẩn danh sách các account không có nhân vật/UID hợp lệ trong phần Redeem Code để báo cáo gọn gàng, chuyên nghiệp hơn.
