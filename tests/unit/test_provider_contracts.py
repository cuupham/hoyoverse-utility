"""Regression cases for provider contract handling; no live requests."""

import asyncio
import json
import runpy
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import aiohttp
import pytest

from src.api.checkin import check_cookie, do_checkin
from src.api.client import _retry_after, parse_provider_envelope, request_json
from src.api.redeem_exchange import exchange_cdkey, redeem_codes_for_region
from src.api.redeem_fetch import fetch_all_uids, fetch_cdkeys
from src.config import STATUS_ERROR, URLS
from src.models.account import Account
from src.models.game import Game
from src.models.results import ProviderResult
from tests.conftest import MockAsyncCM


@pytest.mark.parametrize(
    "game,payload",
    [
        (Game.GENSHIN, {"gt_result": {"is_risk": True}}),
        (Game.STAR_RAIL, {"is_risk": True}),
        (
            Game.ZZZ,
            {"risk_code": 375, "gt": "challenge-provider", "challenge": "challenge"},
        ),
    ],
)
async def test_challenge_is_not_a_success(mock_account, game, payload):
    info = {"is_sign": False, "total_sign_day": 1, "error": None, "retcode": 0}
    response = {"success": True, "data": {"retcode": 0, "data": payload}}
    with (
        patch("src.api.checkin.get_checkin_info", new=AsyncMock(return_value=info)),
        patch("src.api.checkin.request_json", new=AsyncMock(return_value=response)),
    ):
        result = await do_checkin(None, mock_account, game)
    assert result["success"] is False
    assert result["day"] is None
    assert result["action_required"] is True


@pytest.mark.parametrize("retcode", [-2001, -2003, -2016])
async def test_rejected_code_does_not_stop_other_codes(mock_account, retcode):
    responses = [
        {
            "success": True,
            "data": {"retcode": retcode, "message": "Provider rejection"},
        },
        {"success": True, "data": {"retcode": 0, "data": {}}},
    ]
    with (
        patch(
            "src.api.redeem_exchange.request_json",
            new=AsyncMock(side_effect=responses),
        ) as api,
        patch("src.api.redeem_exchange.asyncio.sleep", new=AsyncMock()),
    ):
        results = await redeem_codes_for_region(
            None, mock_account, Game.GENSHIN, "asia", "000000", ["FIRST", "SECOND"]
        )
    assert api.await_count == 2
    assert results["SECOND"]["success"] is True


async def test_provider_message_has_precedence(mock_account):
    response = {
        "success": True,
        "data": {"retcode": -2017, "message": "Provider-specific detail"},
    }
    with patch(
        "src.api.redeem_exchange.request_json", new=AsyncMock(return_value=response)
    ):
        result = await exchange_cdkey(
            None, mock_account, Game.GENSHIN, "asia", "000000", "CODE"
        )
    assert result["message"] == "Provider-specific detail"


def test_activity_urls_use_configured_provider_host():
    for group in ("checkin_info", "checkin_sign"):
        assert all(
            url.startswith("https://sg-act-public-api.hoyolab.com/")
            for url in URLS[group].values()
        )


def test_empty_credentials_rejected():
    with pytest.raises(ValueError):
        Account.from_cookie_string(
            "AUDIT", "_MHYUUID=; _HYVUUID=; cookie_token_v2=; account_id_v2="
        )


def test_account_repr_does_not_include_credentials(mock_account):
    assert mock_account.cookie_str not in repr(mock_account)
    assert "mock_cookie_token" not in repr(mock_account)


@pytest.mark.parametrize(
    "envelope", [None, [], "wrong", {}, {"retcode": True}, {"retcode": "0"}]
)
async def test_provider_parser_rejects_invalid_envelopes_after_http_success(envelope):
    response = MagicMock(status=200, json=AsyncMock(return_value=envelope))
    session = MagicMock(request=MagicMock(return_value=MockAsyncCM(response)))
    with patch("src.api.client.asyncio.sleep", new=AsyncMock()):
        result = await request_json(session, "https://example.test/read", {})
    assert result["success"]
    parsed = parse_provider_envelope(result)
    assert not parsed.success
    assert parsed.error_kind == "invalid_response"


@pytest.mark.parametrize("method,retry", [("POST", True), ("GET", False)])
async def test_mutating_request_not_retried_after_timeout(method, retry):
    session = MagicMock(
        request=MagicMock(return_value=MockAsyncCM(side_effect=asyncio.TimeoutError()))
    )
    with patch("src.api.client.asyncio.sleep", new=AsyncMock()):
        result = await request_json(
            session, "https://example.test/action", {}, method=method, retry=retry
        )
    assert result["error"] == "timeout"
    assert session.request.call_count == 1


async def test_http_error_not_treated_as_provider_success():
    response = MagicMock(status=401, json=AsyncMock(return_value={"retcode": 0}))
    session = MagicMock(request=MagicMock(return_value=MockAsyncCM(response)))
    with patch("src.api.client.asyncio.sleep", new=AsyncMock()):
        result = await request_json(session, "https://example.test/read", {})
    assert result["status"] == 401
    assert not result["success"]
    response.json.assert_not_awaited()


async def test_invalid_json_is_reported():
    response = MagicMock(
        status=200, json=AsyncMock(side_effect=json.JSONDecodeError("invalid", "", 0))
    )
    session = MagicMock(request=MagicMock(return_value=MockAsyncCM(response)))
    with patch("src.api.client.asyncio.sleep", new=AsyncMock()):
        result = await request_json(session, "https://example.test/read", {})
    assert result["error"] == "invalid_json"


async def test_retry_after_wait_releases_response_and_permit():
    semaphore = asyncio.Semaphore(1)
    state = {"closed": False}

    class ResponseContext(MockAsyncCM):
        async def __aexit__(self, *args):
            state["closed"] = True

    limited = MagicMock(status=429, headers={"Retry-After": "3"})
    ok = MagicMock(status=200, json=AsyncMock(return_value={"retcode": 0}))
    session = MagicMock(
        request=MagicMock(side_effect=[ResponseContext(limited), MockAsyncCM(ok)])
    )
    waits = []

    async def sleep(delay):
        if delay == 3:
            assert state["closed"]
            assert not semaphore.locked()
        waits.append(delay)

    with (
        patch("src.api.client._get_semaphore", return_value=semaphore),
        patch("src.api.client.asyncio.sleep", side_effect=sleep),
    ):
        result = await request_json(session, "https://example.test/read", {})
    assert result["success"]
    assert 3 in waits


async def test_long_retry_after_returns_failure_without_retrying_early():
    response = MagicMock(status=429, headers={"Retry-After": "3600"})
    session = MagicMock(request=MagicMock(return_value=MockAsyncCM(response)))
    with patch("src.api.client.asyncio.sleep", new=AsyncMock()) as sleep:
        result = await request_json(session, "https://example.test/read", {})
    assert not result["success"]
    assert session.request.call_count == 1
    assert all(call.args[0] < 1 for call in sleep.await_args_list)


def test_retry_after_dates_and_invalid_values():
    future = format_datetime(
        datetime.now(timezone.utc) + timedelta(seconds=20), usegmt=True
    )
    assert 0 < _retry_after(future, 5) <= 20
    assert _retry_after("invalid", 5) == 5
    assert _retry_after(None, 5) == 5
    assert _retry_after("²", 5) == 5


async def test_truncated_sign_response_reconciles_without_resubmit(mock_account):
    response = MagicMock(
        status=200,
        json=AsyncMock(side_effect=aiohttp.ClientPayloadError("Truncated response")),
    )
    session = MagicMock(request=MagicMock(return_value=MockAsyncCM(response)))
    before = {"is_sign": False, "total_sign_day": 1, "error": None}
    after = {"is_sign": True, "total_sign_day": 2, "error": None}
    with (
        patch(
            "src.api.checkin.get_checkin_info",
            new=AsyncMock(side_effect=[before, after]),
        ),
        patch("src.api.client.asyncio.sleep", new=AsyncMock()),
    ):
        result = await do_checkin(session, mock_account, Game.GENSHIN)
    assert result["success"]
    assert result["day"] == 2
    assert session.request.call_count == 1


def test_redeem_status_keeps_numeric_error():
    from src.utils.display import _short_redeem_status

    assert (
        _short_redeem_status(
            {"success": False, "message": "Provider detail", "retcode": -2016}
        )
        == f"{STATUS_ERROR} [-2016] Provider detail"
    )


def test_fetch_failure_not_displayed_as_no_codes():
    from src.config import SYSTEM_MESSAGES
    from src.utils.display import display_redeem

    with patch("src.utils.display.log_print") as printed:
        display_redeem({}, {}, ["CDKeys: timeout"])
    printed.assert_any_call(SYSTEM_MESSAGES["REDEEM_FETCH_FAILED"])
    assert call(SYSTEM_MESSAGES["REDEEM_NONE"]) not in printed.call_args_list


@pytest.mark.parametrize("data", [None, [], "wrong"])
def test_payload_validation(data):
    result = parse_provider_envelope(
        {"success": True, "data": {"retcode": 0, "data": data}}
    )
    assert not result.success


def test_missing_retcode_is_not_a_success():
    assert not parse_provider_envelope({"success": True, "data": {}}).success


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"is_sign": "false", "total_sign_day": 1},
        {"is_sign": False, "total_sign_day": -1},
    ],
)
async def test_invalid_info_does_not_trigger_sign(mock_account, payload):
    response = {"success": True, "data": {"retcode": 0, "data": payload}}
    with patch(
        "src.api.checkin.request_json", new=AsyncMock(return_value=response)
    ) as api:
        result = await do_checkin(None, mock_account, Game.GENSHIN)
    assert not result["success"]
    assert api.await_count == 1


@pytest.mark.parametrize(
    "failure",
    [
        {"success": False, "error": "timeout", "message": "Request timed out"},
        {"success": True, "data": {"retcode": -5003, "message": "Already signed"}},
    ],
)
async def test_ambiguous_sign_reconciles_state_without_resubmit(mock_account, failure):
    before = {"is_sign": False, "total_sign_day": 1, "error": None}
    after = {"is_sign": True, "total_sign_day": 2, "error": None}
    with (
        patch(
            "src.api.checkin.get_checkin_info",
            new=AsyncMock(side_effect=[before, after]),
        ) as info,
        patch(
            "src.api.checkin.request_json", new=AsyncMock(return_value=failure)
        ) as sign,
    ):
        result = await do_checkin(None, mock_account, Game.GENSHIN)
    assert result["success"]
    assert result["day"] == 2
    assert info.await_count == 2
    assert sign.await_count == 1


async def test_sign_failure_retcode_preserved(mock_account):
    before = {"is_sign": False, "total_sign_day": 1, "error": None}
    with (
        patch("src.api.checkin.get_checkin_info", new=AsyncMock(return_value=before)),
        patch(
            "src.api.checkin.request_json",
            new=AsyncMock(
                return_value={
                    "success": True,
                    "data": {"retcode": -100, "message": "Please log in"},
                }
            ),
        ),
    ):
        result = await do_checkin(None, mock_account, Game.GENSHIN)
    assert not result["success"]
    assert result["retcode"] == -100


async def test_malformed_risk_payload_does_not_succeed(mock_account):
    with (
        patch(
            "src.api.checkin.get_checkin_info",
            new=AsyncMock(
                return_value={"is_sign": False, "total_sign_day": 1, "error": None}
            ),
        ),
        patch(
            "src.api.checkin.request_json",
            new=AsyncMock(
                return_value={
                    "success": True,
                    "data": {"retcode": 0, "data": {"gt_result": None}},
                }
            ),
        ),
    ):
        assert not (await do_checkin(None, mock_account, Game.GENSHIN))["success"]


async def test_cookie_null_data_does_not_crash(mock_account):
    with patch(
        "src.api.checkin.request_json",
        new=AsyncMock(
            return_value={"success": True, "data": {"retcode": 0, "data": None}}
        ),
    ):
        assert not (await check_cookie(None, mock_account))["valid"]


@pytest.mark.parametrize(
    "modules",
    [
        None,
        [None],
        [{"exchange_group": []}],
        [{"exchange_group": {"bonuses": "wrong"}}],
        [{"exchange_group": {"bonuses": [None]}}],
        [{"exchange_group": {"bonuses": [{"exchange_code": 12}]}}],
    ],
)
async def test_malformed_material_is_an_error(mock_account, modules):
    response = {"success": True, "data": {"retcode": 0, "data": {"modules": modules}}}
    with patch(
        "src.api.redeem_fetch.request_json", new=AsyncMock(return_value=response)
    ):
        result = await fetch_cdkeys(None, mock_account, Game.GENSHIN)
    assert not result.success
    assert result.error


async def test_null_exchange_group_and_deduplication(mock_account):
    modules = [
        {"exchange_group": None},
        {"exchange_group": {}},
        {
            "exchange_group": {
                "bonuses": [
                    {},
                    {"exchange_code": " CODE "},
                    {"exchange_code": "CODE"},
                    {"exchange_code": ""},
                ]
            }
        },
    ]
    response = {"success": True, "data": {"retcode": 0, "data": {"modules": modules}}}
    with patch(
        "src.api.redeem_fetch.request_json", new=AsyncMock(return_value=response)
    ):
        result = await fetch_cdkeys(None, mock_account, Game.GENSHIN)
    assert result.success
    assert result.data == ["CODE"]


@pytest.mark.parametrize(
    "roles",
    [
        None,
        [None],
        [{"game_biz": []}],
        [{"game_biz": "hkrpg_global", "region": [], "game_uid": "123"}],
    ],
)
async def test_malformed_roles_are_an_error(mock_account, roles):
    response = {"success": True, "data": {"retcode": 0, "data": {"list": roles}}}
    with patch(
        "src.api.redeem_fetch.request_json", new=AsyncMock(return_value=response)
    ):
        assert not (await fetch_all_uids(None, mock_account)).success


def test_conflicting_required_cookie_rejected(mock_account):
    with pytest.raises(ValueError, match="Conflicting cookie key"):
        Account.from_cookie_string(
            "AUDIT", mock_account.cookie_str + "; _MHYUUID=other"
        )


def test_repeated_optional_cookie_keeps_last_value(mock_account):
    account = Account.from_cookie_string(
        "AUDIT", mock_account.cookie_str + "; mi18nLang=en; mi18nLang=vi"
    )
    assert account.cookies["mi18nLang"] == "vi"


async def test_health_assertion_rejects_transport_failure(mock_account):
    path = Path(__file__).resolve().parents[1] / "api_health" / "test_api_health.py"
    health = runpy.run_path(str(path))
    method = health["TestCDKeyFetchEndpoint"].test_cdkey_fetch_responds
    with patch.dict(
        method.__globals__,
        {
            "fetch_cdkeys": AsyncMock(
                return_value=ProviderResult([], error="Network connection failed")
            )
        },
    ):
        with pytest.raises(AssertionError, match="Network connection failed"):
            await method(
                health["TestCDKeyFetchEndpoint"](), None, mock_account, Game.GENSHIN
            )
    assert "TestRedeemEndpoint" not in health
