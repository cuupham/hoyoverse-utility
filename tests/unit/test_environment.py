"""Tests grouped by their implementation owner."""

import os
from unittest.mock import patch

from src.utils.environment import account_sort_key, get_accounts_from_env


class TestEnvironmentAccounts:
    def test_get_accounts_from_env_filtering(self):
        mock_env = {
            "ACC_PLAYER1": "cookie1",
            "ACC_PLAYER2": "cookie2",
            "NOT_AN_ACC": "something",
            "ACC_EMPTY": "",
            "ACC_WHITESPACE": "   ",
            "OTHER_VAR": "val",
        }
        with patch.dict(os.environ, mock_env, clear=True):
            accounts = get_accounts_from_env()
            assert len(accounts) == 2
            assert "ACC_WHITESPACE" not in accounts


def test_account_sort_key_orders_numbers_naturally():
    names = ["ACC_10", "ACC_2", "ACC_1", "ACC_B", "ACC_a"]
    assert sorted(names, key=account_sort_key) == [
        "ACC_1",
        "ACC_2",
        "ACC_10",
        "ACC_a",
        "ACC_B",
    ]
