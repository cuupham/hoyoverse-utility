"""Tests cho main.py - tất cả functions và exit paths"""

from unittest.mock import AsyncMock, patch

import pytest

import src.main as main_module
from src.config import STATUS_ERROR, SYSTEM_MESSAGES
from src.models.game import Game
from src.models.results import AccountValidationResult, ProviderResult, RedemptionData


@pytest.fixture
def valid_cookie():
    return "ltoken_v2=v; ltuid_v2=1; cookie_token_v2=c; account_id_v2=a; _MHYUUID=m; _HYVUUID=h"


class TestPrintHeader:
    def test_prints_header(self):
        with patch("src.main.log_print") as mock_log:
            main_module.print_header()
        first = mock_log.call_args_list[0].args[0]
        assert "HOYOLAB AUTO TOOL" in first
        assert main_module.ctx.trace_id in first


class TestRunCheckin:
    @pytest.mark.asyncio
    async def test_returns_dict_by_account_name(self, mock_session, mock_accounts):
        mock_result = {game: {"success": True, "message": "OK"} for game in Game}
        with patch(
            "src.main.run_checkin_for_account",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await main_module.run_checkin(mock_session, mock_accounts)

        assert "ACC_1" in result
        assert "ACC_2" in result


class TestFetchRedemptionData:
    async def test_returns_cdkeys_and_uids(self, mock_session, mock_accounts):
        uids = {game: {"asia": "123"} for game in Game}
        with (
            patch(
                "src.main.fetch_cdkeys",
                new=AsyncMock(return_value=ProviderResult(["CODE1"])),
            ) as fetch,
            patch(
                "src.main.fetch_all_uids",
                new=AsyncMock(return_value=ProviderResult(uids)),
            ),
        ):
            result = await main_module.fetch_redemption_data(
                mock_session, mock_accounts
            )
        assert result.cdkeys == {game: ["CODE1"] for game in Game}
        assert set(result.account_uids) == {"ACC_1", "ACC_2"}
        assert result.errors == []
        assert fetch.await_count == 3

    async def test_fallback_is_per_game_and_preserves_partial_results(
        self, mock_session, mock_accounts
    ):
        calls = []

        async def fetch(session, account, game):
            calls.append((account.name, game))
            if account.name == "ACC_1" and game is not Game.GENSHIN:
                return ProviderResult([], error="timeout")
            return ProviderResult([game.value.code])

        with (
            patch("src.main.fetch_cdkeys", side_effect=fetch),
            patch(
                "src.main.fetch_all_uids",
                new=AsyncMock(return_value=ProviderResult({game: {} for game in Game})),
            ),
        ):
            result = await main_module.fetch_redemption_data(
                mock_session, mock_accounts
            )
        assert result.cdkeys == {game: [game.value.code] for game in Game}
        assert result.errors == []
        assert ("ACC_2", Game.GENSHIN) not in calls
        assert len(calls) == 5

    async def test_successful_empty_is_distinct_from_failed_fetch(
        self, mock_session, mock_accounts
    ):
        async def fetch(session, account, game):
            return (
                ProviderResult([])
                if game is Game.GENSHIN
                else ProviderResult([], error="timeout")
            )

        with (
            patch("src.main.fetch_cdkeys", side_effect=fetch),
            patch(
                "src.main.fetch_all_uids",
                new=AsyncMock(return_value=ProviderResult({}, error="Please log in")),
            ),
        ):
            result = await main_module.fetch_redemption_data(
                mock_session, mock_accounts
            )
        assert result.cdkeys == {Game.GENSHIN: []}
        assert result.account_uids == {}
        assert len(result.errors) == 4
        assert any("timeout" in error for error in result.errors)
        assert any("Please log in" in error for error in result.errors)

    async def test_returns_empty_when_all_accounts_empty(
        self, mock_session, mock_accounts
    ):
        with (
            patch(
                "src.main.fetch_cdkeys", new=AsyncMock(return_value=ProviderResult([]))
            ),
            patch(
                "src.main.fetch_all_uids",
                new=AsyncMock(return_value=ProviderResult({game: {} for game in Game})),
            ),
        ):
            result = await main_module.fetch_redemption_data(
                mock_session, mock_accounts
            )
        assert result.cdkeys == {game: [] for game in Game}
        assert result.errors == []

    async def test_empty_accounts(self, mock_session):
        result = await main_module.fetch_redemption_data(mock_session, [])
        assert result == RedemptionData({game: [] for game in Game}, {})


class TestRunRedeemForAll:
    @pytest.mark.asyncio
    async def test_filters_eligible_accounts(self, mock_session, mock_accounts):
        cdkeys = {Game.GENSHIN: ["CODE1"], Game.STAR_RAIL: [], Game.ZZZ: []}
        # ACC_1 có UID, ACC_2 không
        account_uids = {
            "ACC_1": {Game.GENSHIN: {"asia": "800"}, Game.STAR_RAIL: {}, Game.ZZZ: {}},
            "ACC_2": {Game.GENSHIN: {}, Game.STAR_RAIL: {}, Game.ZZZ: {}},
        }

        with patch(
            "src.main.run_redeem_for_account", new_callable=AsyncMock, return_value={}
        ) as mock_redeem:
            result = await main_module.run_redeem_for_all(
                mock_session, mock_accounts, cdkeys, account_uids
            )

        assert mock_redeem.call_count == 1  # chỉ ACC_1
        assert "ACC_1" in result

    @pytest.mark.asyncio
    async def test_no_eligible_returns_empty(self, mock_session, mock_accounts):
        cdkeys = {game: ["CODE1"] for game in Game}
        account_uids = {
            "ACC_1": {game: {} for game in Game},
            "ACC_2": {game: {} for game in Game},
        }

        result = await main_module.run_redeem_for_all(
            mock_session, mock_accounts, cdkeys, account_uids
        )
        assert result == {}


class TestMainExitPaths:
    async def test_fetch_error_fails_run_and_closes_session(
        self, mock_account, valid_cookie
    ):
        session = AsyncMock()
        session.__aenter__.return_value = session
        data = RedemptionData({}, {}, ["CDKeys / Genshin Impact: timeout"])
        with (
            patch(
                "src.main.get_accounts_from_env", return_value={"ACC_1": valid_cookie}
            ),
            patch("src.main.print_header"),
            patch("src.main.create_session", return_value=session),
            patch(
                "src.main.validate_accounts",
                new=AsyncMock(return_value=AccountValidationResult([mock_account])),
            ),
            patch("src.main.run_checkin", new=AsyncMock(return_value={})),
            patch("src.main.fetch_redemption_data", new=AsyncMock(return_value=data)),
            patch("src.main.display_checkin"),
            patch("src.main.display_redeem") as display,
            patch("src.main.run_redeem_for_all", new=AsyncMock()) as redeem,
            pytest.raises(SystemExit, match="1"),
        ):
            await main_module.main()
        display.assert_called_once_with({}, {}, data.errors)
        redeem.assert_not_awaited()
        session.__aexit__.assert_awaited_once()

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
            patch(
                "src.main.get_accounts_from_env", return_value={"ACC_1": "bad_cookie"}
            ),
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
            patch(
                "src.main.get_accounts_from_env", return_value={"ACC_1": valid_cookie}
            ),
            patch("src.main.print_header"),
            patch("src.main.log_error"),
            patch("src.main.create_session", return_value=mock_session),
            patch(
                "src.main.validate_accounts",
                new_callable=AsyncMock,
                return_value=AccountValidationResult([]),
            ),
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
            patch(
                "src.main.get_accounts_from_env", return_value={"ACC_1": valid_cookie}
            ),
            patch("src.main.print_header"),
            patch("src.main.create_session", return_value=mock_session),
            patch(
                "src.main.validate_accounts",
                new_callable=AsyncMock,
                return_value=AccountValidationResult([mock_account]),
            ),
            patch("src.main.run_checkin", new_callable=AsyncMock, return_value={}),
            patch(
                "src.main.fetch_redemption_data",
                new_callable=AsyncMock,
                return_value=RedemptionData(empty_cdkeys, {}),
            ),
            patch("src.main.display_checkin"),
            patch("src.main.display_redeem"),
            patch("src.main.run_redeem_for_all", new_callable=AsyncMock) as mock_redeem,
            patch("src.main.log_print"),
        ):
            await main_module.main()
            mock_redeem.assert_not_called()

    @pytest.mark.asyncio
    async def test_full_flow_with_codes_and_redeem_results(
        self, mock_account, valid_cookie
    ):
        """Full flow có codes + redeem kết quả → gọi display_redeem_results (cover main.py:148)"""
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        cdkeys = {Game.GENSHIN: ["CODE1"], Game.STAR_RAIL: [], Game.ZZZ: []}
        uids = {
            "ACC_1": {Game.GENSHIN: {"asia": "800"}, Game.STAR_RAIL: {}, Game.ZZZ: {}}
        }
        redeem_results = {
            "ACC_1": {Game.GENSHIN: {"asia": {"CODE1": {"success": True}}}}
        }

        with (
            patch(
                "src.main.get_accounts_from_env", return_value={"ACC_1": valid_cookie}
            ),
            patch("src.main.print_header"),
            patch("src.main.create_session", return_value=mock_session),
            patch(
                "src.main.validate_accounts",
                new_callable=AsyncMock,
                return_value=AccountValidationResult([mock_account]),
            ),
            patch("src.main.run_checkin", new_callable=AsyncMock, return_value={}),
            patch(
                "src.main.fetch_redemption_data",
                new_callable=AsyncMock,
                return_value=RedemptionData(cdkeys, uids),
            ),
            patch("src.main.display_checkin"),
            patch("src.main.display_redeem"),
            patch("src.main.display_redeem_results") as mock_display,
            patch(
                "src.main.run_redeem_for_all",
                new_callable=AsyncMock,
                return_value=redeem_results,
            ),
            patch("src.main.log_print"),
        ):
            await main_module.main()
            mock_display.assert_called_once_with(redeem_results)

    @pytest.mark.asyncio
    async def test_codes_without_matching_uids_is_not_a_failure(
        self, mock_account, valid_cookie
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        cdkeys = {Game.GENSHIN: ["CODE1"], Game.STAR_RAIL: [], Game.ZZZ: []}
        uids = {"ACC_1": {game: {} for game in Game}}

        with (
            patch(
                "src.main.get_accounts_from_env", return_value={"ACC_1": valid_cookie}
            ),
            patch("src.main.print_header"),
            patch("src.main.create_session", return_value=mock_session),
            patch(
                "src.main.validate_accounts",
                new_callable=AsyncMock,
                return_value=AccountValidationResult([mock_account]),
            ),
            patch("src.main.run_checkin", new_callable=AsyncMock, return_value={}),
            patch(
                "src.main.fetch_redemption_data",
                new_callable=AsyncMock,
                return_value=RedemptionData(cdkeys, uids),
            ),
            patch("src.main.display_checkin"),
            patch("src.main.display_redeem"),
            patch("src.main.display_redeem_results"),
            patch(
                "src.main.run_redeem_for_all", new_callable=AsyncMock, return_value={}
            ),
            patch("src.main.log_error") as mock_error,
            patch("src.main.log_print") as mock_print,
        ):
            await main_module.main()
        mock_error.assert_not_called()
        assert any(
            SYSTEM_MESSAGES["REDEEM_NO_ELIGIBLE"] in str(c)
            for c in mock_print.call_args_list
        )


class TestFetchRedemptionDataEmpty:
    @pytest.mark.asyncio
    async def test_empty_accounts_returns_empty(self, mock_session):
        """Empty accounts produce empty redemption data without fetch errors."""
        from src.main import fetch_redemption_data

        result = await fetch_redemption_data(mock_session, [])
        assert all(codes == [] for codes in result.cdkeys.values())
        assert result.account_uids == {}
        assert result.errors == []


def _checkin(status, **extra):
    return {
        "success": status in {"claimed", "already_claimed"},
        "status": status,
        "message": "msg",
        **extra,
    }


class TestFailureCollection:
    def test_checkin_failures_skip_missing_character(self):
        results = {
            "ACC_1": {
                Game.GENSHIN: _checkin("no_character"),
                Game.STAR_RAIL: _checkin("already_claimed"),
                Game.ZZZ: _checkin("failed", message="boom", retcode=-1),
            }
        }
        assert main_module._checkin_failures(results) == [
            "ACC_1 · Zenless Zone Zero · [-1] boom"
        ]

    def test_redeem_failures_skip_provider_rejections(self):
        results = {
            "ACC_1": {
                Game.GENSHIN: {
                    "asia": {
                        "USED": {
                            "success": False,
                            "message": "used",
                            "error_kind": "provider",
                        },
                        "OK": {"success": True, "message": "ok"},
                        "LOST": {
                            "success": False,
                            "message": "net",
                            "error_kind": "network",
                        },
                    }
                }
            }
        }
        assert main_module._redeem_failures(results) == [
            "ACC_1 · Genshin Impact · asia · LOST · net"
        ]


class TestValidateAccountsOutput:
    @pytest.mark.asyncio
    async def test_lists_each_account_and_reports_errors_once(
        self, mock_session, mock_accounts
    ):
        checks = [
            {"valid": True, "email_mask": "v****@example.com", "error": None},
            {"valid": False, "email_mask": None, "error": "expired"},
        ]
        lines = []
        with (
            patch("src.main.check_cookie", side_effect=checks),
            patch("src.main.log_print", side_effect=lambda m="": lines.append(m)),
        ):
            result = await main_module.validate_accounts(mock_session, mock_accounts)

        assert lines[0] == "ACCOUNTS  1/2 hợp lệ"
        assert lines[1].split() == ["ACC_1", "v****@example.com"]
        assert lines[2].split() == ["ACC_2", STATUS_ERROR]
        assert result.errors == ["ACC_2 · expired"]


class TestMainReporting:
    @pytest.mark.asyncio
    async def test_failed_run_reports_result_and_writes_summary(
        self, mock_account, valid_cookie
    ):
        session = AsyncMock()
        session.__aenter__.return_value = session
        results = {
            "ACC_1": {
                game: _checkin("failed", message="boom", retcode=-1) for game in Game
            }
        }

        with (
            patch(
                "src.main.get_accounts_from_env", return_value={"ACC_1": valid_cookie}
            ),
            patch("src.main.print_header"),
            patch("src.main.create_session", return_value=session),
            patch(
                "src.main.validate_accounts",
                new_callable=AsyncMock,
                return_value=AccountValidationResult([mock_account]),
            ),
            patch("src.main.run_checkin", new_callable=AsyncMock, return_value=results),
            patch(
                "src.main.fetch_redemption_data",
                new_callable=AsyncMock,
                return_value=RedemptionData({game: [] for game in Game}, {}),
            ),
            patch("src.main.display_checkin"),
            patch("src.main.display_redeem"),
            patch("src.main.display_result") as display_result,
            patch("src.main.write_job_summary") as write_summary,
            pytest.raises(SystemExit, match="1"),
        ):
            await main_module.main()

        failures = display_result.call_args.args[1]
        assert len(failures) == len(Game)
        assert write_summary.call_args.args[:2] == (results, failures)
