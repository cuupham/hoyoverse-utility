"""Live credentials are loaded only when a live test requests the fixture."""

from collections.abc import AsyncIterator

import aiohttp
import pytest
import pytest_asyncio

from src.api.client import create_session
from src.models.account import Account
from tests.support.accounts import load_live_accounts


@pytest.fixture(scope="session")
def live_accounts() -> list[Account]:
    try:
        accounts = load_live_accounts()
    except ValueError as error:
        pytest.fail(str(error))
    if not accounts:
        pytest.skip("No live accounts. Set ACC_* or tests/auth/.env.ps1")
    return accounts


@pytest.fixture(scope="session")
def live_account(live_accounts: list[Account]) -> Account:
    return live_accounts[0]


@pytest_asyncio.fixture
async def live_session() -> AsyncIterator[aiohttp.ClientSession]:
    async with create_session() as session:
        yield session
