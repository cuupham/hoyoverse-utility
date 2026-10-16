"""Runtime account configuration from ACC_* environment variables."""

import os


def get_accounts_from_env() -> dict[str, str]:
    return {
        name: cookie
        for name, cookie in os.environ.items()
        if name.startswith("ACC_") and cookie.strip()
    }
