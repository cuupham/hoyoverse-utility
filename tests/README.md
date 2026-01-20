# tests - Public Testing Environment

Thư mục này chứa các file logic testing công khai của project.
**LƯU Ý:** Thông tin nhạy cảm (cookies) phải được để ở file `.env.ps1` tại thư mục gốc và file này đã được chặn bởi `.gitignore`.

## Cấu trúc

```
project_root/
├── .env.ps1              # [BÍ MẬT] PowerShell set cookies (tạo từ file template)
├── tests/                # [CÔNG KHAI]
│   ├── __init__.py       # Package init
│   ├── conftest.py       # Pytest fixtures & mock data
│   ├── test_redeem.py    # Test cases cho redeem functionality
│   ├── test_core.py      # Test models & core logic
│   ├── pytest.ini        # Pytest configuration
│   └── cookies.ps1.example # Template file hướng dẫn set cookies
```

## Hướng dẫn sử dụng

### 1. Set cookies để test với API thực
Để chạy test hoặc tool với dữ liệu thật, bạn cần tạo file `.env.ps1`:
1. Copy `tests/cookies.ps1.example` ra thư mục gốc và đổi tên thành `.env.ps1`.
2. Điền cookie của bạn vào.
3. Chạy file bằng PowerShell:
```powershell
. .\.env.ps1
```

### 2. Chạy unit tests (Mock data)
Bộ test này sử dụng mock data nên có thể chạy mà không cần cookie thật:
```powershell
# Cài pytest
pip install pytest pytest-asyncio

# Chạy toàn bộ tests
pytest tests -v

# Chạy từng file test
pytest tests/test_redeem.py -v
```

## Mock Data có sẵn

| Fixture | Mô tả |
|---------|-------|
| `mock_account` | 1 account mock |
| `mock_accounts` | List 2 accounts |
| `mock_cdkeys_all_games` | CDKeys cho 3 games |
| `mock_cdkeys_partial` | CDKeys cho 1 số games |
| `mock_cdkeys_empty` | Không có codes |
| `mock_cdkeys_invalid` | Codes không hợp lệ |
| `mock_uids_all_regions` | UIDs cho tất cả regions |
| `mock_uids_partial` | UIDs cho 1 số regions |
| `mock_uids_empty` | Không có UIDs |
| `mock_redeem_*` | Các API responses |
