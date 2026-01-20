# 🎮 HoYoLab Auto Tool

Tự động **điểm danh hàng ngày** và **nhập redeem code** cho 3 game Hoyoverse thông qua GitHub Actions.

## ✨ Features

| Feature | Mô tả |
|---------|-------|
| 礼物 **Auto Check-in** | Điểm danh hàng ngày nhận rewards |
| 🔑 **Auto Redeem** | Tự động nhập codes mới nhất |
| 🔄 **Multi-Account** | Hỗ trợ nhiều tài khoản |
| ⚡ **Cross-region Skip** | Skip codes hết hạn tự động |
| 🚀 **High Performance** | Tối ưu tốc độ với kiến trúc chạy song song (Parallel) |

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
│   └── hoyo-flow.yml       # GitHub Actions workflow
├── tests/                  # Public test suite
│   ├── test_checkin.py
│   ├── test_redeem.py
│   ├── conftest.py
│   └── cookies.ps1.example  # Template cho local test
├── .env.ps1                # Local cookie store (gitignored)
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

# Set environment (local testing)
# 1. Copy tests/cookies.ps1.example -> .env.ps1
# 2. Điền cookies vào .env.ps1
# 3. Chạy file:
.\.env.ps1

# Run
python -m src.main

# Test (Mock data - không cần cookie)
pip install pytest pytest-asyncio
pytest tests -v
```

## 📊 Output Example

```
20/01/2026 07:38:22 [INFO] ==================================================
20/01/2026 07:38:22 [INFO] HOYOLAB AUTO TOOL
20/01/2026 07:38:23 [INFO] ==================================================
20/01/2026 07:38:23 [INFO] --- KIỂM TRA ACCOUNTS ---
20/01/2026 07:38:23 [INFO] [✓] ACC_1: Hợp lệ (u****@gmail.com)
20/01/2026 07:38:23 [INFO]
20/01/2026 07:38:24 [INFO] --- CHECK-IN ---
20/01/2026 07:38:24 [INFO] === ACC_1 ===
20/01/2026 07:38:24 [INFO]   Genshin Impact: ✓ Điểm danh thành công (Ngày 15)
20/01/2026 07:38:24 [INFO]   Honkai: Star Rail: ✓ Đã điểm danh trước đó
20/01/2026 07:38:24 [INFO]
20/01/2026 07:38:24 [INFO] --- REDEEM CODE ---
20/01/2026 07:38:24 [INFO] >> Fetching CDKeys...
20/01/2026 07:38:24 [INFO] [SYSTEM] Genshin Impact: 3 codes [ABC, DEF, XYZ]
20/01/2026 07:38:24 [INFO]
20/01/2026 07:38:24 [INFO] === ACC_1 ===
20/01/2026 07:38:24 [INFO]   Genshin Impact:
20/01/2026 07:38:24 [INFO]     os_asia:
20/01/2026 07:38:24 [INFO]       ABC: ✓ Thành công
20/01/2026 07:38:24 [INFO]
20/01/2026 07:38:24 [INFO] ==================================================
20/01/2026 07:38:24 [INFO] DONE - 1.1s
20/01/2026 07:38:24 [INFO] ==================================================
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
