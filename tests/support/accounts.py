"""Load local verification accounts without executing PowerShell or logging secrets."""

import re
from pathlib import Path

from src.models.account import Account
from src.utils.environment import get_accounts_from_env

DEFAULT_COOKIE_FILE = Path(__file__).resolve().parents[1] / "auth" / ".env.ps1"


def load_live_accounts(cookie_file: Path = DEFAULT_COOKIE_FILE) -> list[Account]:
    """Prefer configured ACC_* values; read the local fallback only when absent."""
    cookies = get_accounts_from_env()
    if not cookies and cookie_file.exists():
        for name, cookie in re.findall(
            r'\$env:(ACC_\d+)\s*=\s*"(.*?)"', cookie_file.read_text(encoding="utf-8")
        ):
            if name in cookies:
                raise ValueError(f"{name}: Duplicate account configuration")
            if cookie.strip():
                cookies[name] = cookie
    return [
        Account.from_cookie_string(name, cookie)
        for name, cookie in sorted(cookies.items())
    ]
