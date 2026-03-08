"""Additional tests to improve codebase coverage (as per audit result)"""

import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock

from src.api.client import _sanitize_error_message, safe_api_call
from src.utils.helpers import get_accounts_from_env
from src.api.redeem import _redeem_game_for_account
from src.models.game import Game


class TestSecurityAudit:
    """Audit tests for security-related functions"""

    def test_error_sanitization_masks_sensitive_info(self):
        """Verify that _sanitize_error_message hides cookies/tokens"""
        # Case 1: Cookie leak
        err1 = Exception("Failed with cookie: ltoken=xyz")
        assert "details hidden" in _sanitize_error_message(err1)

        # Case 2: Token leak
        err2 = Exception("Auth failed for token 12345")
        assert "details hidden" in _sanitize_error_message(err2)

        # Case 3: Safe error
        err3 = Exception("Connection refused by host")
        assert "Connection refused" in _sanitize_error_message(err3)

        # Case 4: Long error truncation
        err4 = Exception("A" * 200)
        sanitized = _sanitize_error_message(err4)
        assert len(sanitized) <= 105
        assert sanitized.endswith("...")


class TestEfficiencyAudit:
    """Audit tests for performance and logic efficiency"""

    @pytest.mark.asyncio
    async def test_safe_api_call_rate_limit_429(self, mock_session):
        """Verify that safe_api_call handles 429 by waiting and retrying"""
        # Mock responses
        mock_resp_429 = MagicMock()
        mock_resp_429.status = 429

        mock_resp_200 = MagicMock()
        mock_resp_200.status = 200
        mock_resp_200.json = AsyncMock(return_value={"retcode": 0})

        # A simple helper to create async context manager mocks
        class MockAsyncContextManager:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        # Force request to be a MagicMock (not AsyncMock) so calling it returns the CM directly
        mock_session.request = MagicMock()
        mock_session.request.side_effect = [
            MockAsyncContextManager(mock_resp_429),
            MockAsyncContextManager(mock_resp_200),
        ]

        with patch("src.api.client.asyncio.sleep") as mock_sleep:
            with patch("src.api.client._get_semaphore"):
                result = await safe_api_call(mock_session, "http://test.com", {})

                assert result["success"] is True
                # Should have slept at least twice (1 for 429, and jitter for attempts)
                assert mock_sleep.call_count >= 2

    @pytest.mark.asyncio
    async def test_cross_region_skip_logic(self, mock_session, mock_account):
        """Verify that a code expiring in one region is skipped in subsequent regions"""
        codes = ["GLOBAL_EXPIRED"]
        # region1: returns expired (-2001)
        # region2: should NOT be called

        uids = {"asia": "800", "usa": "600"}

        # Mock exchange_cdkey to track calls
        with patch("src.api.redeem.exchange_cdkey") as mock_exchange:
            # First call returns expired
            mock_exchange.return_value = {"success": False, "message": "Expired", "retcode": -2001}

            with patch("src.api.redeem.asyncio.sleep"):  # Skip delays
                results = await _redeem_game_for_account(mock_session, mock_account, Game.GENSHIN, codes, uids)

        # exchange_cdkey should only be called ONCE (for asia)
        assert mock_exchange.call_count == 1

        # results for usa should be 'skipped'
        assert results["usa"]["GLOBAL_EXPIRED"]["skipped"] is True
        assert "skip" in results["usa"]["GLOBAL_EXPIRED"]["message"].lower()


class TestEnvironmentAudit:
    """Audit tests for environment and configuration loading"""

    def test_get_accounts_from_env_filtering(self):
        """Verify that only ACC_ variables are loaded"""
        mock_env = {
            "ACC_PLAYER1": "cookie1",
            "ACC_PLAYER2": "cookie2",
            "NOT_AN_ACC": "something",
            "ACC_EMPTY": "",
            "OTHER_VAR": "val",
        }
        with patch.dict(os.environ, mock_env, clear=True):
            accounts = get_accounts_from_env()
            assert len(accounts) == 2
            assert "ACC_PLAYER1" in accounts
            assert "ACC_PLAYER2" in accounts
            assert "NOT_AN_ACC" not in accounts
            assert "ACC_EMPTY" not in accounts
