"""Regressions for operational errors, ambiguous writes and local diagnostics."""

import asyncio
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import src.main as app
from src.api.checkin import check_cookie, do_checkin
from src.api.client import _get_semaphore
from src.api.request_builder import generate_browser_headers
from src.models.game import Game
from src.models.results import AccountValidationResult, RedemptionData
from tests.support.accounts import load_live_accounts


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {"gt_result": None},
        {"gt_result": {"is_risk": "false"}},
        {"is_risk": []},
        {"risk_code": "0"},
        {"challenge": False},
        {"gt": {}},
    ],
)
async def test_malformed_sign_payload_reconciles_without_second_post(
    mock_account, payload
):
    before = {"is_sign": False, "total_sign_day": 1, "error": None}
    after = {"is_sign": True, "total_sign_day": 2, "error": None}
    with (
        patch(
            "src.api.checkin.get_checkin_info",
            new=AsyncMock(side_effect=[before, after]),
        ) as info,
        patch(
            "src.api.checkin.request_json",
            new=AsyncMock(
                return_value={"success": True, "data": {"retcode": 0, "data": payload}}
            ),
        ) as sign,
    ):
        result = await do_checkin(None, mock_account, Game.GENSHIN)
    assert result["success"]
    assert result["status"] == "already_claimed"
    assert result["day"] == 2
    assert info.await_count == 2
    assert sign.await_count == 1
    assert sign.call_args.kwargs["retry"] is False


@pytest.mark.parametrize(
    "response,status",
    [
        (
            {"success": False, "error": "timeout", "message": "Request timed out"},
            "check_failed",
        ),
        ({"success": True, "data": {"retcode": 0, "data": None}}, "check_failed"),
        (
            {"success": True, "data": {"retcode": -100, "message": "Please login"}},
            "invalid_credentials",
        ),
    ],
)
async def test_cookie_check_separates_bad_credentials_from_operational_failure(
    mock_account, response, status
):
    with patch("src.api.checkin.request_json", new=AsyncMock(return_value=response)):
        result = await check_cookie(None, mock_account)
    assert not result["valid"]
    assert result["status"] == status
    assert result["error"]


@pytest.mark.parametrize(
    "checkin_status,redeem_error,validation_error,expected_exit",
    [
        ("failed", None, False, 1),
        ("challenge", None, False, 1),
        ("no_character", None, False, 0),
        ("claimed", "provider", False, 0),
        ("claimed", "network", False, 1),
        ("claimed", None, True, 1),
    ],
)
async def test_run_outcome_distinguishes_expected_rejections_and_operational_errors(
    mock_account, checkin_status, redeem_error, validation_error, expected_exit
):
    session = AsyncMock()
    session.__aenter__.return_value = session
    validation = AccountValidationResult(
        [mock_account], ["ACC_OTHER: check failed"] if validation_error else []
    )
    checkin = {
        mock_account.name: {
            game: {
                "success": checkin_status == "claimed",
                "status": checkin_status,
                "message": "Unrelated translated message",
                "day": 1,
            }
            for game in Game
        }
    }
    cdkeys = {Game.GENSHIN: ["CODE"]} if redeem_error else {}
    data = RedemptionData(cdkeys, {mock_account.name: {Game.GENSHIN: {"asia": "000"}}})
    redemption = {
        mock_account.name: {
            Game.GENSHIN: {
                "asia": {
                    "CODE": {
                        "success": False,
                        "message": "Rejected",
                        "error_kind": redeem_error,
                    }
                }
            }
        }
    }
    with (
        patch.object(
            app,
            "get_accounts_from_env",
            return_value={mock_account.name: mock_account.cookie_str},
        ),
        patch.object(app, "create_session", return_value=session),
        patch.object(app, "validate_accounts", new=AsyncMock(return_value=validation)),
        patch.object(app, "run_checkin", new=AsyncMock(return_value=checkin)),
        patch.object(app, "fetch_redemption_data", new=AsyncMock(return_value=data)),
        patch.object(
            app, "run_redeem_for_all", new=AsyncMock(return_value=redemption)
        ) as redeem,
        patch.object(app, "display_checkin"),
        patch.object(app, "display_redeem"),
        patch.object(app, "display_redeem_results"),
        patch.object(app, "log_print"),
    ):
        if expected_exit:
            with pytest.raises(SystemExit) as exited:
                await app.main()
            assert exited.value.code == expected_exit
        else:
            await app.main()
    session.__aexit__.assert_awaited_once()
    assert redeem.await_count == int(bool(redeem_error))


def test_generated_browser_profile_is_consistently_windows_desktop():
    for _ in range(20):
        headers = generate_browser_headers()
        assert "Windows NT" in headers["user-agent"]
        assert "Android" not in headers["user-agent"]
        assert headers["sec-ch-ua-platform"] == '"Windows"'
        assert headers["sec-ch-ua-mobile"] == "?0"


def test_browser_generator_constrains_profile_selection():
    agent = MagicMock(chrome="Mozilla/5.0 (Windows NT 10.0) Chrome/142.0")
    with patch("src.api.request_builder.UserAgent", return_value=agent) as factory:
        generate_browser_headers()
    assert factory.call_args.kwargs["os"] == ["Windows"]
    assert factory.call_args.kwargs["platforms"] == ["desktop"]


def test_semaphore_is_not_reused_across_event_loops():
    async def semaphore():
        return _get_semaphore()

    assert asyncio.run(semaphore()) is not asyncio.run(semaphore())


def test_local_account_loader_prefers_env_without_reading_fallback(
    mock_account, tmp_path
):
    with (
        patch(
            "tests.support.accounts.get_accounts_from_env",
            return_value={"ACC_1": mock_account.cookie_str},
        ),
        patch.object(
            Path, "read_text", side_effect=AssertionError("must not read fallback")
        ),
    ):
        accounts = load_live_accounts(tmp_path / ".env.ps1")
    assert accounts[0].name == "ACC_1"


def test_local_account_loader_reads_only_explicit_fallback(mock_account, tmp_path):
    cookie_file = tmp_path / ".env.ps1"
    cookie_file.write_text(
        f'$env:ACC_1 = "{mock_account.cookie_str}"', encoding="utf-8"
    )
    with patch("tests.support.accounts.get_accounts_from_env", return_value={}):
        accounts = load_live_accounts(cookie_file)
    assert accounts[0].cookie_str == mock_account.cookie_str


def test_debug_help_works_outside_repository_without_credentials(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "debug_checkin_info.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Read-only diagnostics" in result.stdout


async def test_missing_characters_do_not_block_other_eligible_games(mock_account):
    cdkeys = {Game.GENSHIN: ["GENSHIN_CODE"], Game.STAR_RAIL: ["RAIL_CODE"]}
    uids = {mock_account.name: {Game.GENSHIN: {"asia": "000"}, Game.STAR_RAIL: {}}}
    with patch.object(
        app,
        "run_redeem_for_account",
        new=AsyncMock(
            return_value={
                Game.GENSHIN: {
                    "asia": {"GENSHIN_CODE": {"success": True, "message": "OK"}}
                }
            }
        ),
    ) as redeem:
        results = await app.run_redeem_for_all(None, [mock_account], cdkeys, uids)
    assert results[mock_account.name][Game.GENSHIN]["asia"]["GENSHIN_CODE"]["success"]
    redeem.assert_awaited_once_with(None, mock_account, cdkeys, uids[mock_account.name])
