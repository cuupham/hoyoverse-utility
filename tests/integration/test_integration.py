"""Integration tests - Verifying the full flow of main.py with mocked network"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

import src.main as main_module
from src.models.results import AccountValidationResult, RedemptionData


class TestIntegrationFlow:
    """Tests for the main orchestration logic"""

    @pytest.mark.asyncio
    async def test_validate_accounts_filter_logic(self, mock_session, mock_accounts):
        """Verify that validate_accounts correctly filters valid/invalid accounts"""
        # acc1 valid, acc2 invalid
        mock_res1 = {"valid": True, "email_mask": "v****@gmail.com", "error": None}
        mock_res2 = {"valid": False, "email_mask": None, "error": "Invalid cookie"}

        with patch("src.main.check_cookie") as mock_check:
            mock_check.side_effect = [mock_res1, mock_res2]

            valid_accs = await main_module.validate_accounts(
                mock_session, mock_accounts
            )

            assert len(valid_accs.valid_accounts) == 1
            assert valid_accs.errors == ["ACC_2: Invalid cookie"]
            assert valid_accs.valid_accounts[0].name == "ACC_1"

    @pytest.mark.asyncio
    async def test_main_orchestration_parallel_execution(self, mock_account):
        """A sequential main flow cannot cross this two-task barrier."""
        checkin_started, fetch_started = asyncio.Event(), asyncio.Event()

        async def checkin(*args):
            checkin_started.set()
            await fetch_started.wait()
            return {}

        async def fetch(*args):
            fetch_started.set()
            await checkin_started.wait()
            return RedemptionData({}, {})

        session = AsyncMock()
        session.__aenter__.return_value = session
        with (
            patch(
                "src.main.get_accounts_from_env",
                return_value={mock_account.name: mock_account.cookie_str},
            ),
            patch("src.main.create_session", return_value=session),
            patch(
                "src.main.validate_accounts",
                new=AsyncMock(return_value=AccountValidationResult([mock_account])),
            ),
            patch("src.main.run_checkin", side_effect=checkin),
            patch("src.main.fetch_redemption_data", side_effect=fetch),
            patch("src.main.display_checkin"),
            patch("src.main.display_redeem"),
            patch("src.main.log_print"),
        ):
            await asyncio.wait_for(main_module.main(), timeout=2)
        assert checkin_started.is_set() and fetch_started.is_set()
        session.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("src.main.create_session")
    @patch("src.main.get_accounts_from_env")
    @patch("src.main.validate_accounts")
    @patch("src.main.run_checkin")
    @patch("src.main.fetch_redemption_data")
    @patch("src.main.run_redeem_for_all")
    async def test_full_main_flow_success(
        self,
        mock_run_redeem,
        mock_fetch_data,
        mock_run_checkin,
        mock_validate,
        mock_get_env,
        mock_session_factory,
        mock_account,
    ):
        """Verify the full main() function flow from start to finish"""
        # Setup mocks
        # Use a VALID mock cookie string from conftest or similar
        valid_cookie = "ltoken_v2=v; ltuid_v2=1; cookie_token_v2=c; account_id_v2=a; _MHYUUID=m; _HYVUUID=h"
        mock_get_env.return_value = {"ACC_1": valid_cookie}

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session_factory.return_value = mock_session

        mock_validate.return_value = AccountValidationResult([mock_account])
        mock_run_checkin.return_value = {}
        mock_fetch_data.return_value = RedemptionData({}, {})
        mock_run_redeem.return_value = {}

        with (
            patch("src.main.display_checkin"),
            patch("src.main.display_redeem"),
            patch("src.main.display_redeem_results"),
        ):
            await main_module.main()

            mock_get_env.assert_called_once()
            mock_validate.assert_called_once()
            mock_run_checkin.assert_called_once()
            mock_fetch_data.assert_called_once()
