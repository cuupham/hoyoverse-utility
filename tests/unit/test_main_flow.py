"""Tests cho main.py - tất cả functions và exit paths"""

import pytest
from unittest.mock import AsyncMock, patch

from src.models.account import Account
from src.models.game import Game
import src.main as main_module


@pytest.fixture
def valid_cookie():
    return "ltoken_v2=v; ltuid_v2=1; cookie_token_v2=c; account_id_v2=a; _MHYUUID=m; _HYVUUID=h"


class TestPrintHeader:
    def test_prints_header(self):
        with patch("src.main.log_print") as mock_log:
            main_module.print_header()
            assert mock_log.call_count >= 4


class TestRunCheckin:
    @pytest.mark.asyncio
    async def test_returns_dict_by_account_name(self, mock_session, mock_accounts):
        mock_result = {game: {"success": True, "message": "OK"} for game in Game}
        with patch("src.main.run_checkin_for_account", new_callable=AsyncMock, return_value=mock_result):
            result = await main_module.run_checkin(mock_session, mock_accounts)

        assert "ACC_1" in result
        assert "ACC_2" in result


class TestFetchAppData:
    @pytest.mark.asyncio
    async def test_returns_cdkeys_and_uids(self, mock_session, mock_accounts):
        mock_cdkeys = {game: ["CODE1"] for game in Game}
        mock_uids = {game: {"asia": "123"} for game in Game}

        with (
            patch("src.main.fetch_all_cdkeys", new_callable=AsyncMock, return_value=mock_cdkeys),
            patch("src.main.fetch_all_uids", new_callable=AsyncMock, return_value=mock_uids),
        ):
            cdkeys, account_uids = await main_module.fetch_app_data(mock_session, mock_accounts)

        assert cdkeys == mock_cdkeys
        assert "ACC_1" in account_uids
        assert "ACC_2" in account_uids

    @pytest.mark.asyncio
    async def test_fallback_when_first_account_returns_empty(self, mock_session, mock_accounts):
        """Khi account đầu trả empty CDKeys, chọn kết quả tốt nhất từ accounts khác"""
        empty_cdkeys = {game: [] for game in Game}
        good_cdkeys = {Game.GENSHIN: ["CODE1", "CODE2"], Game.STAR_RAIL: [], Game.ZZZ: []}
        mock_uids = {game: {} for game in Game}

        call_count = 0

        async def mock_fetch_cdkeys(session, account):
            nonlocal call_count
            call_count += 1
            # Account đầu trả empty, account sau trả codes
            return empty_cdkeys if call_count == 1 else good_cdkeys

        with (
            patch("src.main.fetch_all_cdkeys", side_effect=mock_fetch_cdkeys),
            patch("src.main.fetch_all_uids", new_callable=AsyncMock, return_value=mock_uids),
        ):
            cdkeys, _ = await main_module.fetch_app_data(mock_session, mock_accounts)

        # Phải chọn kết quả có nhiều codes hơn
        assert cdkeys == good_cdkeys
        assert call_count == 2


class TestRunRedeemForAll:
    @pytest.mark.asyncio
    async def test_filters_eligible_accounts(self, mock_session, mock_accounts):
        cdkeys = {Game.GENSHIN: ["CODE1"], Game.STAR_RAIL: [], Game.ZZZ: []}
        # ACC_1 có UID, ACC_2 không
        account_uids = {
            "ACC_1": {Game.GENSHIN: {"asia": "800"}, Game.STAR_RAIL: {}, Game.ZZZ: {}},
            "ACC_2": {Game.GENSHIN: {}, Game.STAR_RAIL: {}, Game.ZZZ: {}},
        }

        with patch("src.main.run_redeem_for_account", new_callable=AsyncMock, return_value={}) as mock_redeem:
            result = await main_module.run_redeem_for_all(mock_session, mock_accounts, cdkeys, account_uids)

        assert mock_redeem.call_count == 1  # chỉ ACC_1
        assert "ACC_1" in result

    @pytest.mark.asyncio
    async def test_no_eligible_returns_empty(self, mock_session, mock_accounts):
        cdkeys = {game: ["CODE1"] for game in Game}
        account_uids = {
            "ACC_1": {game: {} for game in Game},
            "ACC_2": {game: {} for game in Game},
        }

        result = await main_module.run_redeem_for_all(mock_session, mock_accounts, cdkeys, account_uids)
        assert result == {}


class TestMainExitPaths:
    @pytest.mark.asyncio
    async def test_no_env_accounts_exits(self):
        with (
            patch("src.main.get_accounts_from_env", return_value={}),
            patch("src.main.print_header"),
            patch("src.main.log_error"),
            pytest.raises(SystemExit, match="1"),
        ):
            await main_module.main()

    @pytest.mark.asyncio
    async def test_all_cookies_invalid_exits(self, valid_cookie):
        with (
            patch("src.main.get_accounts_from_env", return_value={"ACC_1": "bad_cookie"}),
            patch("src.main.print_header"),
            patch("src.main.log_error"),
            pytest.raises(SystemExit, match="1"),
        ):
            await main_module.main()

    @pytest.mark.asyncio
    async def test_all_validation_failed_exits(self, valid_cookie):
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session

        with (
            patch("src.main.get_accounts_from_env", return_value={"ACC_1": valid_cookie}),
            patch("src.main.print_header"),
            patch("src.main.log_error"),
            patch("src.main.create_session", return_value=mock_session),
            patch("src.main.validate_accounts", new_callable=AsyncMock, return_value=[]),
            pytest.raises(SystemExit, match="1"),
        ):
            await main_module.main()

    @pytest.mark.asyncio
    async def test_full_flow_no_codes(self, mock_account, valid_cookie):
        """Full flow khi không có codes → skip redeem"""
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        empty_cdkeys = {game: [] for game in Game}

        with (
            patch("src.main.get_accounts_from_env", return_value={"ACC_1": valid_cookie}),
            patch("src.main.print_header"),
            patch("src.main.create_session", return_value=mock_session),
            patch("src.main.validate_accounts", new_callable=AsyncMock, return_value=[mock_account]),
            patch("src.main.run_checkin", new_callable=AsyncMock, return_value={}),
            patch("src.main.fetch_app_data", new_callable=AsyncMock, return_value=(empty_cdkeys, {})),
            patch("src.main.display_checkin"),
            patch("src.main.display_redeem"),
            patch("src.main.run_redeem_for_all", new_callable=AsyncMock) as mock_redeem,
            patch("src.main.log_print"),
        ):
            await main_module.main()
            mock_redeem.assert_not_called()

    @pytest.mark.asyncio
    async def test_full_flow_with_codes_and_redeem_results(self, mock_account, valid_cookie):
        """Full flow có codes + redeem kết quả → gọi display_redeem_results (cover main.py:148)"""
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        cdkeys = {Game.GENSHIN: ["CODE1"], Game.STAR_RAIL: [], Game.ZZZ: []}
        uids = {"ACC_1": {Game.GENSHIN: {"asia": "800"}, Game.STAR_RAIL: {}, Game.ZZZ: {}}}
        redeem_results = {"ACC_1": {Game.GENSHIN: {"asia": {"CODE1": {"success": True}}}}}

        with (
            patch("src.main.get_accounts_from_env", return_value={"ACC_1": valid_cookie}),
            patch("src.main.print_header"),
            patch("src.main.create_session", return_value=mock_session),
            patch("src.main.validate_accounts", new_callable=AsyncMock, return_value=[mock_account]),
            patch("src.main.run_checkin", new_callable=AsyncMock, return_value={}),
            patch("src.main.fetch_app_data", new_callable=AsyncMock, return_value=(cdkeys, uids)),
            patch("src.main.display_checkin"),
            patch("src.main.display_redeem"),
            patch("src.main.display_redeem_results") as mock_display,
            patch("src.main.run_redeem_for_all", new_callable=AsyncMock, return_value=redeem_results),
            patch("src.main.log_print"),
        ):
            await main_module.main()
            mock_display.assert_called_once_with(redeem_results)

    @pytest.mark.asyncio
    async def test_full_flow_with_codes_no_uids(self, mock_account, valid_cookie):
        """Full flow khi có codes nhưng không có UIDs"""
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        cdkeys = {Game.GENSHIN: ["CODE1"], Game.STAR_RAIL: [], Game.ZZZ: []}
        uids = {"ACC_1": {game: {} for game in Game}}

        with (
            patch("src.main.get_accounts_from_env", return_value={"ACC_1": valid_cookie}),
            patch("src.main.print_header"),
            patch("src.main.create_session", return_value=mock_session),
            patch("src.main.validate_accounts", new_callable=AsyncMock, return_value=[mock_account]),
            patch("src.main.run_checkin", new_callable=AsyncMock, return_value={}),
            patch("src.main.fetch_app_data", new_callable=AsyncMock, return_value=(cdkeys, uids)),
            patch("src.main.display_checkin"),
            patch("src.main.display_redeem"),
            patch("src.main.display_redeem_results"),
            patch("src.main.run_redeem_for_all", new_callable=AsyncMock, return_value={}),
            patch("src.main.log_print") as mock_log,
        ):
            await main_module.main()
            # Phải log "no UIDs" message
            log_calls = [str(c) for c in mock_log.call_args_list]
            assert any("UID" in c for c in log_calls)


