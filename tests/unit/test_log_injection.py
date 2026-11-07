"""Provider-controlled text must never reach logs as a forged workflow command."""

from unittest.mock import patch

import pytest

from src.api.checkin import check_cookie
from src.api.client import parse_provider_envelope
from src.api.redeem_fetch import fetch_all_uids, fetch_cdkeys
from src.models.game import Game
from src.utils.sanitize import has_unsafe_chars, sanitize_remote_text

FORGED = "ok\n::stop-commands::token\r\n::error::fake ::warning::x"


class TestSanitize:
    def test_removes_line_breaks_and_collapses_whitespace(self):
        cleaned = sanitize_remote_text(FORGED)
        assert "\n" not in cleaned and "\r" not in cleaned and " " not in cleaned
        assert not any(line.startswith("::") for line in cleaned.splitlines())

    @pytest.mark.parametrize("text", ["plain text", "Không có code", "ABC-123 xyz"])
    def test_printable_text_is_unchanged(self, text):
        assert sanitize_remote_text(text) == text
        assert not has_unsafe_chars(text)

    @pytest.mark.parametrize("text", ["a\nb", "a\x00b", "a​b", "a b"])
    def test_unsafe_characters_are_detected(self, text):
        assert has_unsafe_chars(text)


def test_provider_message_is_single_line():
    parsed = parse_provider_envelope(
        {"success": True, "data": {"retcode": -1, "message": FORGED}}
    )
    assert "\n" not in parsed.error and "\r" not in parsed.error
    assert " " not in parsed.error


def test_message_that_is_only_control_chars_falls_back_to_retcode():
    parsed = parse_provider_envelope(
        {"success": True, "data": {"retcode": -7, "message": "\n\r\x00"}}
    )
    assert parsed.error == "Error -7"


@pytest.mark.asyncio
async def test_email_mask_is_sanitized(mock_session, mock_account):
    response = {
        "success": True,
        "data": {"retcode": 0, "data": {"email_mask": "a****@x.com\n::error::boom"}},
    }
    with patch("src.api.checkin.request_json", return_value=response):
        result = await check_cookie(mock_session, mock_account)
    assert result["valid"] is True
    assert "\n" not in result["email_mask"]


@pytest.mark.asyncio
@pytest.mark.parametrize("code", ["ABC\n::stop-commands::x", "AB C", "AB​C"])
async def test_cdkey_with_unsafe_characters_is_rejected(
    mock_session, mock_account, code
):
    response = {
        "success": True,
        "data": {
            "retcode": 0,
            "data": {
                "modules": [{"exchange_group": {"bonuses": [{"exchange_code": code}]}}]
            },
        },
    }
    with patch("src.api.redeem_fetch.request_json", return_value=response):
        result = await fetch_cdkeys(mock_session, mock_account, Game.GENSHIN)
    assert not result.success
    assert result.error_kind == "invalid_response"
    assert result.data == []


@pytest.mark.asyncio
async def test_non_ascii_digit_uid_is_rejected(mock_session, mock_account):
    response = {
        "success": True,
        "data": {
            "retcode": 0,
            "data": {
                "list": [
                    {
                        "game_biz": Game.GENSHIN.value.game_biz,
                        "region": "os_asia",
                        "game_uid": "²³",
                    }
                ]
            },
        },
    }
    with patch("src.api.redeem_fetch.request_json", return_value=response):
        result = await fetch_all_uids(mock_session, mock_account)
    assert not result.success
    assert result.error_kind == "invalid_response"
