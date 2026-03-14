# Error Handling & Output format

## 7. Output Format (Console)

Header và footer dùng `config.HEADER_WIDTH` ký tự `=` (mặc định 50); thời gian format `Time: %Y-%m-%d %H:%M:%S` (từ `main.print_header()`).

```
==================================================
HOYOLAB AUTO TOOL
Time: 2026-01-20 07:50:58
Trace: a83cd482
==================================================

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
==================================================
DONE - 1.0s
==================================================
```

### 7.1. Chiến lược Centralized Logging (Gom log)

Để tối ưu hiệu năng (chạy song song) mà vẫn giữ log dễ đọc, tool áp dụng chiến lược:

1.  **API functions:** Chỉ thực thi logic và `return` kết quả dưới dạng dictionary. Không gọi các hàm in log.
2.  **Display functions:** Các hàm `display_checkin()` và `display_redeem()` trong `main.py` nhận kết quả thô và định dạng chúng thành các block log đẹp mắt.

**Lợi ích:**
- Không bị xen kẽ (interleave) log khi nhiều account chạy cùng lúc.
- Tốc độ xử lý song song nhưng hiển thị tuần tự cho con người dễ đọc.

### 7.2. Logger Architecture

Để chống xen kẽ log (interleave) trong môi trường async, sử dụng `ForceFlushStreamHandler(logging.StreamHandler)` để *force buffer flush* sau mỗi log record. Xem implementation tại `src/utils/logger.py`.

```python
# src/utils/logger.py - Key components:
# - ForceFlushStreamHandler: Custom handler force flush sau mỗi log
# - TraceIdFilter: Filter thêm trace_id vào mỗi log record
# - ExecutionContext: Singleton chứa trace_id, start_time, reset_timer(), elapsed_seconds
# - Named logger 'hoyolab' (không dùng root logger, tránh conflict)
# - log_info(), log_error(), log_print()
```

**Environment variable:** `DEBUG` — bật DEBUG level logs (mặc định: INFO).

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
> **Thứ tự ưu tiên tin nhắn lỗi & Centralized Strings:** 
> 
> Luôn hiển thị thông báo trả về trực tiếp từ API HoYoLab (`data.message`) trước. Chỉ khi server không gửi thông báo mới sử dụng các hằng cấu hình trong hệ thống từ `config.py`.
> 
> Từ phiên bản v2, toàn bộ hard-coded text (Ví dụ: "Điểm danh thành công", "Network connection failed") đều được cấu hình tập trung ở biến Dictionary `SYSTEM_MESSAGES` trong `config.py`. Điều này đảm bảo chuẩn Mực cấu hình SSOT (Single Source of Truth) giúp việc cập nhật/dịch ngôn ngữ trở nên dễ dàng tuyệt đối ở 1 điểm duy nhất.


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
            return SYSTEM_MESSAGES["ERR_UNKNOWN_SECURE"]

    return error_str[:100] + "..." if len(error_str) > 100 else error_str


async def safe_api_call(
    session, url, headers, params=None, json_data=None,
    method="GET", max_retries=MAX_RETRIES,
) -> dict[str, Any]:
    """Pattern xử lý exception với retry cho tất cả API calls"""
    # ... setup kwargs ...

    for attempt in range(max_retries):
        try:
            # Per-attempt timeout giảm dần (floor: MIN_REQUEST_TIMEOUT)
            attempt_timeout = aiohttp.ClientTimeout(
                total=max(REQUEST_TIMEOUT / remaining_attempts, MIN_REQUEST_TIMEOUT),
                connect=CONNECT_TIMEOUT,
            )

            async with _get_semaphore():
                # Anti-detection jitter (0.1-0.3s) bên trong semaphore
                await asyncio.sleep(random.uniform(0.1, 0.3))
                async with session.request(method, url, **kwargs) as resp:
                    if resp.status in _RETRYABLE_STATUS_CODES:  # 429, 5xx
                        # Retry with backoff
                        continue
                    return {"success": True, "data": await resp.json()}

        except aiohttp.ClientConnectionError: ...  # retry with exponential backoff
        except asyncio.TimeoutError: ...            # retry with exponential backoff
        except aiohttp.ContentTypeError: ...        # no retry
        except Exception as e: ...                  # sanitize & return

    return {"success": False, "error": "max_retries", "message": f"Failed after {max_retries} attempts"}
```

### 8.5. Semaphore giới hạn Concurrent Requests

> [!NOTE]
> Semaphore đã được tích hợp trong `safe_api_call` (xem `src/api/client.py`).
> - `SEMAPHORE_LIMIT = 20` concurrent requests max
> - Ví dụ: 48 requests → chỉ 20 chạy cùng lúc, còn lại đợi


### 8.6. Execution Context (Logging Correlation)

Mỗi lần chạy script cần có `trace_id` để dễ debug trong logs:

```python
# src/utils/logger.py
import uuid
import logging
from datetime import datetime

_LOGGER_NAME = "hoyolab"

class TraceIdFilter(logging.Filter):
    """Filter thêm trace_id vào mỗi log record"""
    def __init__(self, trace_id: str):
        super().__init__()
        self.trace_id = trace_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = self.trace_id
        return True

class ForceFlushStreamHandler(logging.StreamHandler):
    """Handler tự động flush buffer sau mỗi dòng log (Tốt cho CI/CD)"""
    def emit(self, record):
        super().emit(record)
        self.flush()

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
        """Setup named logger 'hoyolab' (không dùng root logger, tránh conflict)"""
        handler = ForceFlushStreamHandler()
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%d/%m/%Y %H:%M:%S"
        ))
        named_logger = logging.getLogger(_LOGGER_NAME)
        named_logger.handlers.clear()
        named_logger.addHandler(handler)
        named_logger.addFilter(TraceIdFilter(self.trace_id))
        named_logger.propagate = False

    def reset_timer(self) -> None:
        """Reset start_time — gọi khi main() bắt đầu."""
        self.start_time = datetime.now()

    @property
    def elapsed_seconds(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

# Global instances
ctx = ExecutionContext()
logger = logging.getLogger(_LOGGER_NAME)

def log_info(account: str, message: str) -> None:
    logger.info(f"[{account}] {message}")

def log_error(account: str, message: str) -> None:
    logger.error(f"[{account}] {message}")

def log_print(message: str = "") -> None:
    """Thay thế print() — multiline: mỗi dòng log riêng."""
    if not message:
        logger.info("")
        return
    for line in message.split("\n"):
        logger.info(line)
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

### 8.7. Decoupled Display Pattern — `src/utils/display.py`

Khi phát triển luồng mới, tuân thủ nguyên tắc:
1. Hàm thực thi (API/Service) trả về TypedDict (xem `src/models/types.py`).
2. Hàm hiển thị (Display) trong `src/utils/display.py` nhận dữ liệu đó và dùng `log_print()` để in ra.

Các display functions hiện có:
- `display_checkin(results)` — Hiển thị kết quả check-in cho tất cả accounts
- `display_cdkeys(cdkeys)` — Hiển thị danh sách CDKeys theo game
- `display_uids(uids)` — Hiển thị danh sách UIDs theo account/game/region
- `display_redeem_results(results)` — Hiển thị kết quả redeem theo account/game/region
- `display_redeem(cdkeys, uids)` — Header redeem (gom CDKeys + UIDs)

```python
# Ví dụ pattern chuẩn trong main.py
checkin_results = await run_checkin(session, accounts)
display_checkin(checkin_results)  # In tuần tự, không xen kẽ

cdkeys, uids = await fetch_app_data(session, accounts)
display_redeem(cdkeys, uids)

redeem_results = await run_redeem_for_all(session, accounts, cdkeys, uids)
display_redeem_results(redeem_results)
```

---

