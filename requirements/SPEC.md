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
- **Fetch result:** Kết quả rỗng thành công phải khác lỗi provider/transport/schema;
  fallback CDKey chạy tuần tự theo account cho từng game.
- **Run status:** Lỗi fetch không được khôi phục hoặc có code nhưng không có UID
  sẽ được báo rõ và kết thúc với exit code 1. Account validation failures,
  check-in failures/challenges and redemption transport/schema errors also fail the run
  after independent work finishes. Known no-character and provider redemption
  rejections remain separate; see [error policy](error_codes.md).

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

### 2.2. Workflow environment variables

The [daily workflow](../.github/workflows/hoyo-flow.yml) explicitly exposes ACC_1 through ACC_4 from repository/environment secrets. It does not export every secret through toJSON. Add a workflow mapping explicitly if more accounts are required in Actions; local runs discover all nonempty ACC_* values.

### 2.3. Cookie Format

```
mi18nLang=en-us; _HYVUUID=xxx; _MHYUUID=xxx; cookie_token_v2=xxx; account_mid_v2=xxx; account_id_v2=xxx; ltoken_v2=xxx; ltmid_v2=xxx; ltuid_v2=xxx; ...
```

**Các giá trị quan trọng cần trích xuất từ cookie:**
- `_MHYUUID` → Dùng cho header `x-rpc-device_id`
- `_HYVUUID` → Dùng cho một số API sign

### 2.4. Account model

[Account](../src/models/account.py) stores raw cookies privately for request headers and a read-only parsed mapping for required fields. Account.from_cookie_string parses supplied text; it does not read environment variables. Blank credentials and duplicate keys are rejected. Frozen attributes plus MappingProxyType prevent normal mutation; credentials are excluded from repr. This does not make Account a supported dictionary key.

## 3. GitHub Actions

[The workflow manifest](../.github/workflows/hoyo-flow.yml) owns schedule, pinned actions, secret allowlist, concurrency, Python version and execution command. Its cron runs at 04:45 UTC+7. [The test workflow](../.github/workflows/test.yml) owns the Python 3.10/3.13 verification matrix. No copied YAML implementation is maintained here.

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

Unit and integration tests use `pytest` kết hợp với `pytest-asyncio` và mock
responses. Live API health checks are separate and read-only; they validate read responses and do not exercise write endpoints.

### 5.1. Cấu trúc Testing

Test ownership follows the current paths under `tests/unit/`,
`tests/integration/`, and `tests/api_health/`; local cookie setup is under
`tests/auth/`. The repository's `pytest.ini` is the source of truth for test
discovery and markers.

### 5.2. Các kịch bản Test quan trọng

- **Session Isolation**: Đảm bảo `ClientSession` dùng `DummyCookieJar` để không bị rò rỉ cookie giữa các tài khoản khi chạy song song.
- **Header Differentiation**: Kiểm tra `x-rpc-*` headers được gửi đúng theo từng loại game (Sol vs Luna).
- **Redeem independence**: Mỗi code và region được thử độc lập; không suy diễn
  Hyl retcode thành expiry hoặc region ineligibility và không suppress code
  khác sau một lỗi.
- **Account Validation**: Đảm bảo cookie được parse chính xác và ném lỗi nếu thiếu các key bắt buộc (`_MHYUUID`, `_HYVUUID`, `cookie_token_v2`, `account_id_v2`).
- **Display Formatting**: Đảm bảo display functions format đúng kết quả check-in, CDKeys, UIDs và redeem results.
- **Fetch UIDs**: Đảm bảo fetch UIDs trong 1 request (map ngược game_biz/region về model) và lọc đúng accounts có UID.
- **Typed fetch and fallback**: Kiểm tra `ProviderResult`/`RedemptionData`, fallback
  per-game theo account, và lỗi chưa khôi phục được hiển thị rõ.
- **Main Flow**: Test orchestration flow end-to-end (validate → check-in → fetch → redeem).

### 5.3. Cách chạy Test

Commands live in the [README](../README.md#local-development) and [tests/README.md](../tests/README.md); CI is defined by `.github/workflows/test.yml`, which owns the checks, Python versions, coverage gate and path filters.

---

## 6. Roadmap & Tương lai (Planned)

### 🌎 Standardized Local Timezone
Tự động lấy múi giờ hệ thống (Local Timezone) thay vì mặc định `Asia/Saigon`. Đảm bảo tính nhất quán khi người dùng chạy tool ở các khu vực khác nhau trên thế giới.

### 🧹 Clean Logistics Report
Cải thiện hiển thị: Tự động ẩn danh sách các account có UID fetch thành công
nhưng mapping rỗng trong phần Redeem Code để báo cáo gọn gàng, chuyên nghiệp hơn.
