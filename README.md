# 🎮 HoYoLab Auto Tool

Tự động **điểm danh hàng ngày** và **nhập redeem code** cho 3 game Hoyoverse thông qua GitHub Actions.

## ✨ Features

| Feature | Mô tả |
|---------|-------|
| 🎁 **Auto Check-in** | Điểm danh hàng ngày nhận rewards |
| 🔑 **Auto Redeem** | Tự động nhập codes mới nhất |
| 🔄 **Multi-Account** | Hỗ trợ nhiều tài khoản |
| ⚡ **Cross-region Skip** | Skip codes hết hạn tự động |

## 🎯 Games Supported

| Game | Check-in | Redeem |
|------|----------|--------|
| Genshin Impact | ✅ | ✅ |
| Honkai: Star Rail | ✅ | ✅ |
| Zenless Zone Zero | ✅ | ✅ |

## 🚀 Quick Start

### 1. Fork Repository

Click **Fork** ở góc phải trên.

### 2. Lấy Cookie

1. Truy cập [HoYoLab](https://www.hoyolab.com) và **đăng nhập**
2. Click vào avatar → **Personal Homepage**
3. Mở **DevTools** (F12) → Tab **Network**
4. Tìm request: `getGameRecordCard?uid=...`
5. Click vào request → **Headers** → Copy giá trị **Cookie**

```
Cookie: mi18nLang=en-us; _MHYUUID=xxx; cookie_token_v2=xxx; account_id_v2=xxx; ...
```

> ⚠️ Cookie này sẽ dán vào GitHub Secrets

### 3. Thêm Secrets

1. Vào repo đã fork → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. **Name**: `ACC_1` (hoặc `ACC_2`, `ACC_3`,...)
4. **Value**: Dán cookie string vừa copy
5. Lặp lại cho mỗi account

> 💡 GitHub Actions sẽ tự nhận diện các biến `ACC_*` khi chạy!

### 4. Chạy Workflow

- **Tự động**: Mỗi ngày lúc **4:45 AM (UTC+7)**
- **Thủ công**: **Actions** → **Daily Run** → **Run workflow**

## 📁 Project Structure

```
├── .github/workflows/
│   └── daily.yml           # GitHub Actions workflow
├── .test_local/            # Local test suite (gitignored)
│   ├── test_checkin.py
│   ├── test_redeem.py
│   └── conftest.py
├── src/
│   ├── main.py             # Entry point
│   ├── config.py           # Constants & configurations
│   ├── api/
│   │   ├── client.py       # HTTP client (retry, semaphore)
│   │   ├── checkin.py      # Check-in APIs
│   │   └── redeem.py       # Redeem code APIs
│   ├── models/
│   │   ├── account.py      # Account model
│   │   └── game.py         # Game & Region models
│   └── utils/
│       ├── headers.py      # Dynamic User-Agent headers
│       ├── helpers.py      # Helper functions
│       ├── logger.py       # Logging utilities
│       └── security.py     # Mask sensitive data
├── docs/
│   └── SPEC.md             # Technical specification
└── requirements.txt
```

## 🔧 Local Development

```bash
# Clone
git clone https://github.com/cuupham/hoyoverse-utility.git
cd hoyoverse-utility

# Create venv
python -m venv .venv
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install deps
pip install -r requirements.txt

# Set environment (local testing only)
$env:ACC_1 = "your_cookie_string"  # PowerShell
# export ACC_1="your_cookie_string"  # Linux/Mac

# Run
python -m src.main

# Test
pip install pytest pytest-asyncio
pytest .test_local
```

## 📊 Output Example

```
============================================================
                    HOYOLAB AUTO TOOL
                    18/01/2026 19:44:37
============================================================

--- KIỂM TRA ACCOUNTS ---
[✓] ACC_1: Hợp lệ (u***@gmail.com)
[✓] ACC_2: Hợp lệ (a***@yahoo.com)

--- CHECK-IN ---
=== ACC_1 ===
  Genshin Impact: ✓ Điểm danh thành công (Ngày 15)
  Honkai: Star Rail: ✓ Đã điểm danh trước đó
  Zenless Zone Zero: ✓ Điểm danh thành công (Ngày 8)

--- REDEEM CODE ---
=== ACC_1 ===
  Genshin [asia]:
    GENSHIN2024: ✓ Thành công
    PRIMOGEMS100: ⏭ Skip (đã biết expired)

============================================================
Thời gian chạy: 0.7 giây
============================================================
```

## ⚠️ Lưu ý

> **KHÔNG** commit cookies vào repository!

- Cookies có giá trị **~1 năm**, sau đó cần lấy lại và update trong Secrets
- Delay 5s giữa mỗi lần nhập code để tránh rate limit
- API có thể thay đổi từ phía Hoyoverse

## 📝 License

MIT License - Chỉ dành cho mục đích cá nhân.

---

<p align="center">
  Made with ❤️ for Travelers, Trailblazers & Proxies
</p>
