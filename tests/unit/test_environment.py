"""Tests grouped by their implementation owner."""

import os
from unittest.mock import patch

from src.utils.environment import get_accounts_from_env


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
