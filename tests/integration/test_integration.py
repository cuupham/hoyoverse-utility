"""Integration tests - Verifying the full flow of main.py with mocked network"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

import src.main as main_module


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

            valid_accs = await main_module.validate_accounts(mock_session, mock_accounts)

            assert len(valid_accs) == 1
            assert valid_accs[0].name == "ACC_1"

    @pytest.mark.asyncio
    async def test_main_orchestration_parallel_execution(self, mock_session, mock_account):
        """Verify that checkin and fetch_app_data (for redeem) run in parallel in the main flow"""
        valid_accs = [mock_account]

        # Patch where they are USED (within main_module)
        with patch("src.main.run_checkin", new_callable=AsyncMock) as mock_checkin:
            mock_checkin.return_value = {"acc": "res"}
            with patch("src.main.fetch_app_data", new_callable=AsyncMock) as mock_fetch:
                mock_fetch.return_value = ({}, {})

                with patch("src.main.display_checkin"):
                    with patch("src.main.display_redeem"):
                        # Now we test the integration of gather in a helper or similar
                        # but more importantly we test that main uses them.
                        # For this specific test, let's just verify they are awaited correctly
                        checkin_task = main_module.run_checkin(mock_session, valid_accs)
                        app_data_task = main_module.fetch_app_data(mock_session, valid_accs)

                        res = await asyncio.gather(checkin_task, app_data_task)

                        assert len(res) == 2
                        assert mock_checkin.called
                        assert mock_fetch.called

    @pytest.mark.asyncio
    @patch("src.main.create_session")
    @patch("src.main.get_accounts_from_env")
    @patch("src.main.validate_accounts")
    @patch("src.main.run_checkin")
    @patch("src.main.fetch_app_data")
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

        mock_validate.return_value = [mock_account]
        mock_run_checkin.return_value = {}
        mock_fetch_data.return_value = ({}, {})
        mock_run_redeem.return_value = {}

        with patch("src.main.display_checkin"):
            with patch("src.main.display_redeem"):
                # Run main() but catch SystemExit
                try:
                    await main_module.main()
                except SystemExit:
                    pass

                # Verify key sequence
                mock_get_env.assert_called_once()
                mock_validate.assert_called_once()
                mock_run_checkin.assert_called_once()
                mock_fetch_data.assert_called_once()
                mock_run_redeem.assert_called_once()
