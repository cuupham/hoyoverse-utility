# Audit: DRY, Single source of truth, Clean code, Refactor

**Lần kiểm tra gần nhất:** 2026-02-09 (sau refactor message skip).

## 1. DRY (Don't Repeat Yourself)

### ✅ Đã đạt
- URL, ORIGINS, timeouts, retcodes, REDEEM_MESSAGES, DEFAULT_TIMEZONE, CHECKIN_ALREADY_SIGNED_KEYWORD: một nơi trong `config.py`.
- Game/region: một nơi trong `models/game.py`; `get_page_info()` dùng chung.
- `build_rpc_headers()` trong `utils/helpers.py` dùng cho redeem + fetch CDKeys + fetch UID.
- `safe_api_call`, `create_session` dùng chung cho mọi API.
- Message skip expired/invalid: `config.REDEEM_SKIP_MESSAGE_EXPIRED`; redeem trả về, display dùng `res['message']`.

### ✅ Đã xử lý (refactor đã áp dụng)
- `"en-us"` → `config.RPC_LANGUAGE`
- `"4"` (client_type / platform) → `config.RPC_CLIENT_TYPE`, `config.RPC_PLATFORM`
- `"Windows NT 10.0"` → `config.RPC_SYS_VERSION`
- `"false"` (show-translated) → `config.RPC_SHOW_TRANSLATED`
- `"HomeGamePage"` → `config.PAGE_NAME_HOME_GAME` (checkin, redeem, game)
- `"HomePage"` → `config.PAGE_NAME_HOME`
- `"en"` (redeem params) → `config.REDEEM_LANG`
- `separators=(",", ":")` → `constants.JSON_SEPARATORS` (checkin, game)
- `COOKIE_CHECK_PAGE_INFO` → định nghĩa trong `config.py` (dùng `PAGE_NAME_HOME` + `JSON_SEPARATORS`)
- Message "⏭ Đã skip (expired/invalid...)" → `config.REDEEM_SKIP_MESSAGE_EXPIRED`; display dùng `res['message']` khi skipped.

---

## 2. Single source of truth

### ✅ Đã đạt
- Cấu hình API (URLs, ORIGINS), settings (timeout, retry, delay), retcode/message: `config.py`.
- Game/region: `models/game.py`.
- Giá trị không phụ thuộc module khác: `constants.py` (DEFAULT_CHROME_VERSION).
- Env (COOKIE_CHECK_APP_VERSION, LOG_LEVEL): đọc trong config/logger, không rải rác.

### ✅ Đã đạt (sau refactor)
- RPC header values và tên trang đã gom vào `config.py`; `JSON_SEPARATORS` trong `constants.py`.

---

## 3. Clean code

### ✅ Đã đạt
- Tên file, hàm, biến rõ ràng.
- Hàm một nhiệm vụ (check_cookie, get_checkin_info, do_checkin, build_rpc_headers, …).
- Tái sử dụng: build_rpc_headers, safe_api_call, Game enum, REGIONS.
- API layer trả dict; display tách trong main.

### ⚠️ Ghi chú
- `checkin.py` build headers thủ công cho cookie check và do_checkin (khác device_id / source_info / body) nên không gộp chung với `build_rpc_headers`; chỉ cần thay literal bằng constant từ config.

---

## 4. Refactor

### Đã làm tốt
- Logic trùng đã được gom (build_rpc_headers, get_page_info, safe_api_call).
- Không có hàm/class trùng chức năng.

### Đã làm (refactor hoàn tất)
1. Đã thêm vào `config.py`: `RPC_*`, `PAGE_NAME_*`, `REDEEM_LANG`, `COOKIE_CHECK_PAGE_INFO`.
2. Đã thêm vào `constants.py`: `JSON_SEPARATORS`.
3. Đã thay literal trong `checkin.py`, `helpers.py`, `redeem.py`, `game.py`.

---

## Kết luận

| Tiêu chí | Trạng thái |
|----------|------------|
| DRY | Đủ (sau refactor) |
| Single source of truth | Đủ |
| Clean code | Đủ |
| Refactor | Đã áp dụng |

**Bước tiếp theo (kiểm chứng):** Kích hoạt venv, cài dependency, chạy test:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r tests/requirements.txt
pytest tests -v
```

---

## Kiểm tra 2026-02-09

- **Literal:** Đã rà soát; message skip expired/invalid được gom thành `REDEEM_SKIP_MESSAGE_EXPIRED`, display dùng `res['message']`.
- **Logic trùng:** Không còn; build_rpc_headers, get_page_info, safe_api_call dùng chung.
- **API/state:** Account/model expose qua property/getter; không truy cập nội bộ từ ngoài.
- **SPEC:** Cấu trúc và flow khớp docs/SPEC.md.
- **Phạm vi:** Đã xét api/checkin, api/redeem, api/client, utils/helpers, models/game, config, main.
- **Refactor áp dụng:** Thêm `REDEEM_SKIP_MESSAGE_EXPIRED`; redeem + main dùng single source.
