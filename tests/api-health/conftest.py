"""Fixtures cho API health check tests - load cookie thật từ env hoặc .env.ps1"""

import os
import re

import pytest
import pytest_asyncio
import aiohttp

from src.models.account import Account
from src.api.client import create_session
from src.utils.helpers import get_accounts_from_env


def _load_accounts_from_env() -> list[Account]:
    """Load accounts từ env vars (ACC_1, ACC_2, ...) - reuse helper từ src"""
    accounts = []
    for name, cookie in sorted(get_accounts_from_env().items()):
        try:
            accounts.append(Account.from_env(name, cookie))
        except ValueError:
            pass
    return accounts


def _load_accounts_from_ps1() -> list[Account]:
    """Fallback: parse tests/auth/.env.ps1 nếu env vars không có"""
    ps1_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "auth", ".env.ps1")
    if not os.path.exists(ps1_path):
        return []

    with open(ps1_path, encoding="utf-8") as f:
        content = f.read()

    accounts = []
    for name, cookie in re.findall(r'\$env:(ACC_\d+)\s*=\s*"(.*?)"', content):
        try:
            accounts.append(Account.from_env(name, cookie))
        except ValueError:
            pass
    return accounts


# Cache accounts 1 lần cho toàn bộ session
_LIVE_ACCOUNTS = _load_accounts_from_env() or _load_accounts_from_ps1()


@pytest.fixture(scope="session")
def live_accounts() -> list[Account]:
    """Danh sách accounts thật - skip nếu không có"""
    if not _LIVE_ACCOUNTS:
        pytest.skip("Không có cookie thật. Set ACC_* env vars hoặc tạo tests/auth/.env.ps1")
    return _LIVE_ACCOUNTS


@pytest.fixture(scope="session")
def live_account(live_accounts: list[Account]) -> Account:
    """Account đầu tiên - dùng cho single-account tests"""
    return live_accounts[0]


@pytest_asyncio.fixture
async def live_session() -> aiohttp.ClientSession:
    """Tạo real aiohttp session cho live requests"""
    session = create_session()
    yield session
    await session.close()
