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

### 7.1. Chiến lược Centrailized Logging (Gom log)

Để tối ưu hiệu năng (chạy song song) mà vẫn giữ log dễ đọc, tool áp dụng chiến lược:

1.  **API functions:** Chỉ thực thi logic và `return` kết quả dưới dạng dictionary. Không gọi các hàm in log.
2.  **Display functions:** Các hàm `display_checkin()` và `display_redeem()` trong `main.py` nhận kết quả thô và định dạng chúng thành các block log đẹp mắt.

**Lợi ích:**
- Không bị xen kẽ (interleave) log khi nhiều account chạy cùng lúc.
- Tốc độ xử lý song song nhưng hiển thị tuần tự cho con người dễ đọc.

### 7.2. Dual Output Mode (LOG_LEVEL)

Hỗ trợ 2 format output thông qua environment variable `LOG_LEVEL`. **Lưu ý:** `LOG_LEVEL` ở đây là **output format** (cách in kết quả), không phải log level (debug/info/warning).

| Mode | Mô tả |
|------|-------|
| `human` | Human-readable (default) |
| `json` | Machine-parseable JSON |
| `both` | Cả 2 format |

**Về cấu trúc Logger (OOP/Best Practice):** Bắt đầu từ bản v2, để chống xen kẽ log (interleave) trong môi trường async hoàn toàn, chúng ta sử dụng một Custom class `ForceFlushStreamHandler(logging.StreamHandler)` để *force buffer flush* sau mỗi log được push. Code chuẩn mục OOP, thay vì monkey-patch hàm gốc.

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

# Note: logger và ctx được import từ phần còn lại của logger.py
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

