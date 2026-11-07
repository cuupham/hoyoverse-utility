"""Runtime account configuration from ACC_* environment variables."""

import os
import re


def account_sort_key(name: str) -> list[str | int]:
    """Natural order so ACC_2 sorts before ACC_10."""
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", name)
    ]


def get_accounts_from_env() -> dict[str, str]:
    return {
        name: cookie
        for name, cookie in os.environ.items()
        if name.startswith("ACC_") and cookie.strip()
    }
