"""Additional tests to improve codebase coverage (as per audit result)"""

import asyncio
import os

import aiohttp
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.api.client import _sanitize_error_message, safe_api_call, reset_semaphore, _get_semaphore
from src.api.redeem_exchange import exchange_cdkey, _redeem_game_for_account
from src.api.checkin import check_cookie, get_checkin_info, do_checkin, run_checkin_for_account
from src.api.redeem_fetch import fetch_cdkeys
from src.models.account import Account
from src.models.game import Game, GameInfo, REGIONS
from src.utils.helpers import get_accounts_from_env, build_rpc_headers, unix_ms
from src.utils.security import mask_uid
from src.utils.logger import log_print
from tests.conftest import MockAsyncCM


# ==================== SECURITY ====================


class TestSecurityAudit:
    def test_error_sanitization_masks_sensitive_info(self):
        err1 = Exception("Failed with cookie: ltoken=xyz")
        assert "details hidden" in _sanitize_error_message(err1)

        err2 = Exception("Auth failed for token 12345")
        assert "details hidden" in _sanitize_error_message(err2)

        err3 = Exception("Connection refused by host")
        assert "Connection refused" in _sanitize_error_message(err3)

        err4 = Exception("A" * 200)
        sanitized = _sanitize_error_message(err4)
        assert len(sanitized) <= 105
        assert sanitized.endswith("...")


# ==================== CLIENT ERROR BRANCHES ====================


class TestSafeApiCallErrors:
    @pytest.fixture(autouse=True)
    def _reset(self):
        reset_semaphore()
        yield
        reset_semaphore()

    @pytest.mark.asyncio
    async def test_rate_limit_429_retry(self, mock_session):
        mock_resp_429 = MagicMock(status=429)
        mock_resp_200 = MagicMock(status=200)
        mock_resp_200.json = AsyncMock(return_value={"retcode": 0})

        mock_session.request = MagicMock(side_effect=[
            MockAsyncCM(return_value=mock_resp_429),
            MockAsyncCM(return_value=mock_resp_200),
        ])

        with (
            patch("src.api.client.asyncio.sleep"),
            patch("src.api.client._get_semaphore"),
        ):
            result = await safe_api_call(mock_session, "http://test.com", {})
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_connection_error_retry_exhausted(self, mock_session):
        """ClientConnectionError → retry → fail"""
        mock_session.request = MagicMock(
            side_effect=[MockAsyncCM(side_effect=aiohttp.ClientConnectionError())] * 2
        )
        with (
            patch("src.api.client.asyncio.sleep"),
            patch("src.api.client._get_semaphore"),
        ):
            result = await safe_api_call(mock_session, "http://test.com", {}, max_retries=2)
            assert result["success"] is False
            assert result["error"] == "network"

    @pytest.mark.asyncio
    async def test_content_type_error_no_retry(self, mock_session):
        """ContentTypeError → immediate fail, no retry"""
        mock_session.request = MagicMock(
            side_effect=[MockAsyncCM(side_effect=aiohttp.ContentTypeError(MagicMock(), MagicMock()))]
        )
        with (
            patch("src.api.client.asyncio.sleep"),
            patch("src.api.client._get_semaphore"),
        ):
            result = await safe_api_call(mock_session, "http://test.com", {})
            assert result["success"] is False
            assert result["error"] == "invalid_json"

    @pytest.mark.asyncio
    async def test_generic_exception_sanitized(self, mock_session):
        """Unknown exception → sanitize message"""
        mock_session.request = MagicMock(
            side_effect=[MockAsyncCM(side_effect=RuntimeError("Something broke"))]
        )
        with (
            patch("src.api.client.asyncio.sleep"),
            patch("src.api.client._get_semaphore"),
        ):
            result = await safe_api_call(mock_session, "http://test.com", {})
            assert result["success"] is False
            assert result["error"] == "unknown"

    @pytest.mark.asyncio
    async def test_all_5xx_retries_exhausted(self, mock_session):
        """Tất cả retries đều 502 → fail"""
        mock_502 = MagicMock(status=502)
        mock_session.request = MagicMock(
            side_effect=[MockAsyncCM(return_value=mock_502)] * 3
        )
        with (
            patch("src.api.client.asyncio.sleep"),
            patch("src.api.client._get_semaphore"),
        ):
            result = await safe_api_call(mock_session, "http://test.com", {}, max_retries=3)
            assert result["success"] is False
            assert "502" in result["message"]

    @pytest.mark.asyncio
    async def test_post_with_json_data(self, mock_session):
        """POST method với json_data"""
        mock_resp = MagicMock(status=200)
        mock_resp.json = AsyncMock(return_value={"retcode": 0})
        mock_session.request = MagicMock(return_value=MockAsyncCM(return_value=mock_resp))

        with (
            patch("src.api.client.asyncio.sleep"),
            patch("src.api.client._get_semaphore"),
        ):
            result = await safe_api_call(
                mock_session, "http://test.com", {}, json_data={"key": "val"}, method="POST"
            )
            assert result["success"] is True
            # Verify json kwarg was passed
            call_kwargs = mock_session.request.call_args[1]
            assert call_kwargs["json"] == {"key": "val"}


# ==================== CHECKIN FAIL PATHS ====================


class TestCheckinFailPaths:
    @pytest.mark.asyncio
    async def test_check_cookie_api_failure(self, mock_session, mock_account):
        """check_cookie khi API call fail"""
        with patch("src.api.checkin.safe_api_call", return_value={"success": False, "message": "timeout"}):
            result = await check_cookie(mock_session, mock_account)
            assert result["valid"] is False
            assert "timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_get_checkin_info_api_failure(self, mock_session, mock_account):
        """get_checkin_info khi API call fail"""
        with patch("src.api.checkin.safe_api_call", return_value={"success": False, "message": "network"}):
            result = await get_checkin_info(mock_session, mock_account, Game.GENSHIN)
            assert result["error"] == "network"
            assert result["is_sign"] is False

    @pytest.mark.asyncio
    async def test_get_checkin_info_retcode_not_zero(self, mock_session, mock_account):
        """get_checkin_info khi retcode != 0"""
        mock_resp = {"success": True, "data": {"retcode": -10002, "message": "No character"}}
        with patch("src.api.checkin.safe_api_call", return_value=mock_resp):
            result = await get_checkin_info(mock_session, mock_account, Game.ZZZ)
            assert result["error"] == "No character"

    @pytest.mark.asyncio
    async def test_do_checkin_sign_post_fail(self, mock_session, mock_account):
        """do_checkin khi sign POST thất bại"""
        not_signed = {"is_sign": False, "total_sign_day": 5, "error": None}
        with (
            patch("src.api.checkin.get_checkin_info", return_value=not_signed),
            patch("src.api.checkin.safe_api_call", return_value={"success": False, "message": "timeout"}),
        ):
            result = await do_checkin(mock_session, mock_account, Game.STAR_RAIL)
            assert result["success"] is False
            assert "timeout" in result["message"]

    @pytest.mark.asyncio
    async def test_do_checkin_sign_retcode_not_zero(self, mock_session, mock_account):
        """do_checkin khi sign POST trả retcode != 0"""
        not_signed = {"is_sign": False, "total_sign_day": 5, "error": None}
        sign_fail = {"success": True, "data": {"retcode": -1, "message": "Server error"}}
        with (
            patch("src.api.checkin.get_checkin_info", return_value=not_signed),
            patch("src.api.checkin.safe_api_call", return_value=sign_fail),
        ):
            result = await do_checkin(mock_session, mock_account, Game.ZZZ)
            assert result["success"] is False
            assert "Server error" in result["message"]


# ==================== REDEEM EDGE CASES ====================


class TestRedeemEdgeCases:
    @pytest.mark.asyncio
    async def test_exchange_unknown_region(self, mock_session, mock_account):
        result = await exchange_cdkey(mock_session, mock_account, Game.GENSHIN, "mars", "123", "CODE")
        assert result["success"] is False
        assert "Unknown region" in result["message"]

    @pytest.mark.asyncio
    async def test_exchange_api_failure(self, mock_session, mock_account):
        with patch("src.api.redeem_exchange.safe_api_call", return_value={"success": False, "message": "timeout"}):
            result = await exchange_cdkey(mock_session, mock_account, Game.GENSHIN, "asia", "800001", "CODE")
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_exchange_unknown_retcode_fallback(self, mock_session, mock_account):
        """retcode không có trong REDEEM_MESSAGES → fallback API message"""
        mock_resp = {"success": True, "data": {"retcode": -9999, "message": "Unknown API error"}}
        with patch("src.api.redeem_exchange.safe_api_call", return_value=mock_resp):
            result = await exchange_cdkey(mock_session, mock_account, Game.GENSHIN, "asia", "800001", "CODE")
            assert result["message"] == "Unknown API error"

    @pytest.mark.asyncio
    async def test_exchange_no_message_no_mapping(self, mock_session, mock_account):
        """retcode không có trong REDEEM_MESSAGES và API không trả message → Error {retcode}"""
        mock_resp = {"success": True, "data": {"retcode": -9999}}
        with patch("src.api.redeem_exchange.safe_api_call", return_value=mock_resp):
            result = await exchange_cdkey(mock_session, mock_account, Game.GENSHIN, "asia", "800001", "CODE")
            assert "Error -9999" in result["message"]

    @pytest.mark.asyncio
    async def test_cross_region_skip_logic(self, mock_session, mock_account):
        codes = ["GLOBAL_EXPIRED"]
        uids = {"asia": "800", "usa": "600"}

        with (
            patch("src.api.redeem_exchange.exchange_cdkey") as mock_exchange,
            patch("src.api.redeem_exchange.asyncio.sleep"),
        ):
            mock_exchange.return_value = {"success": False, "message": "Expired", "retcode": -2001}
            results = await _redeem_game_for_account(mock_session, mock_account, Game.GENSHIN, codes, uids)

        assert mock_exchange.call_count == 1
        assert results["usa"]["GLOBAL_EXPIRED"]["skipped"] is True


# ==================== ENVIRONMENT ====================


class TestEnvironmentAudit:
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


# ==================== HELPERS & GAME MODEL ====================


class TestBuildRpcHeaders:
    def test_basic_headers(self, mock_account):
        headers = build_rpc_headers(mock_account, "hoyolab", '{"page":"test"}', "TestPage")
        assert headers["Cookie"] == mock_account.cookie_str
        assert headers["x-rpc-device_id"] == mock_account.mhy_uuid
        assert headers["x-rpc-page_name"] == "TestPage"
        assert "x-rpc-signgame" not in headers

    def test_with_game_signgame(self, mock_account):
        headers = build_rpc_headers(
            mock_account, "hoyolab", '{}', "Page", game=Game.STAR_RAIL
        )
        assert headers["x-rpc-signgame"] == "hkrpg"

    def test_without_game_no_signgame(self, mock_account):
        headers = build_rpc_headers(mock_account, "hoyolab", '{}', "Page", game=Game.GENSHIN)
        assert "x-rpc-signgame" not in headers

    def test_unix_ms(self):
        ts = unix_ms()
        assert isinstance(ts, int)
        assert ts > 1_000_000_000_000  # after year 2001 in ms


class TestGameInfoMethods:
    def test_get_sign_payload_genshin(self):
        gs = Game.GENSHIN.value
        payload = gs.get_sign_payload()
        assert "act_id" in payload
        assert "lang" not in payload  # Genshin doesn't include lang

    def test_get_sign_payload_star_rail(self):
        sr = Game.STAR_RAIL.value
        payload = sr.get_sign_payload()
        assert "act_id" in payload
        assert payload["lang"] == "en-us"

    def test_get_sign_headers_genshin_specific(self, mock_account):
        gs = Game.GENSHIN.value
        headers = gs.get_sign_headers(mock_account, Game.GENSHIN, "TestPage")
        assert headers["content-type"] == "application/json;charset=UTF-8"
        assert headers["x-rpc-app_version"] == ""
        assert headers["x-rpc-device_name"] == ""

    def test_get_sign_headers_star_rail_no_extras(self, mock_account):
        sr = Game.STAR_RAIL.value
        headers = sr.get_sign_headers(mock_account, Game.STAR_RAIL, "TestPage")
        assert "content-type" not in headers
        assert "x-rpc-device_name" not in headers

    def test_get_page_info_non_home_game(self):
        gs = Game.GENSHIN.value
        import json
        data = json.loads(gs.get_page_info("OtherPage"))
        assert data["pageArrangement"] == ""  # not "Hot"

    def test_regions_completeness(self):
        """Mỗi game phải có 4 regions"""
        for game in Game:
            assert len(REGIONS[game]) == 4, f"{game.value.name} thiếu regions"


# ==================== ACCOUNT EDGE CASES ====================


class TestAccountEdgeCases:
    def test_empty_cookie_string(self):
        with pytest.raises(ValueError, match="empty"):
            Account.from_env("ACC", "")

    def test_whitespace_only_cookie(self):
        with pytest.raises(ValueError, match="empty"):
            Account.from_env("ACC", "   ")

    def test_cookie_pair_without_equals(self):
        """Pairs như 'justvalue' bị skip"""
        cookie = "justvalue; _MHYUUID=m; _HYVUUID=h; cookie_token_v2=c; account_id_v2=a"
        acc = Account.from_env("ACC", cookie)
        assert "justvalue" not in acc.cookies

    def test_frozen_dataclass(self):
        cookie = "_MHYUUID=m; _HYVUUID=h; cookie_token_v2=c; account_id_v2=a"
        acc = Account.from_env("ACC", cookie)
        with pytest.raises(AttributeError):
            acc.name = "new_name"


# ==================== MASK UID BOUNDARIES ====================


class TestMaskUidBoundaries:
    def test_exactly_min_length(self):
        """UID đúng 6 ký tự (MIN_UID_LENGTH) → masked entirely"""
        assert mask_uid("123456") == "***"

    def test_one_above_min(self):
        """UID 7 ký tự → partial mask"""
        assert mask_uid("1234567") == "123***567"

    def test_empty_string(self):
        assert mask_uid("") == "***"

    def test_zero_int(self):
        assert mask_uid(0) == "***"


# ==================== SEMAPHORE & CLIENT MISSING LINES ====================


class TestSemaphore:
    @pytest.fixture(autouse=True)
    def _reset(self):
        reset_semaphore()
        yield
        reset_semaphore()

    def test_lazy_init(self):
        """_get_semaphore() lazy init tạo Semaphore khi chưa có"""
        import asyncio
        sem = _get_semaphore()
        assert isinstance(sem, asyncio.Semaphore)

    def test_reuses_existing(self):
        """Gọi 2 lần trả về cùng instance"""
        sem1 = _get_semaphore()
        sem2 = _get_semaphore()
        assert sem1 is sem2

    @pytest.mark.asyncio
    async def test_safe_api_call_with_params(self, mock_session):
        """Verify params kwarg gets passed through"""
        mock_resp = MagicMock(status=200)
        mock_resp.json = AsyncMock(return_value={"retcode": 0})
        mock_session.request = MagicMock(return_value=MockAsyncCM(return_value=mock_resp))

        with (
            patch("src.api.client.asyncio.sleep"),
            patch("src.api.client._get_semaphore"),
        ):
            result = await safe_api_call(
                mock_session, "http://test.com", {}, params={"key": "val"}
            )
            assert result["success"] is True
            call_kwargs = mock_session.request.call_args[1]
            assert call_kwargs["params"] == {"key": "val"}

    @pytest.mark.asyncio
    async def test_timeout_all_retries_exhausted(self, mock_session):
        """Tất cả retries timeout → max_retries error"""
        mock_session.request = MagicMock(
            side_effect=[MockAsyncCM(side_effect=asyncio.TimeoutError())] * 2
        )
        with (
            patch("src.api.client.asyncio.sleep"),
            patch("src.api.client._get_semaphore"),
        ):
            result = await safe_api_call(mock_session, "http://test.com", {}, max_retries=2)
            assert result["success"] is False
            assert result["error"] == "timeout"


# ==================== CHECKIN run_checkin_for_account ====================


class TestRunCheckinForAccount:
    @pytest.mark.asyncio
    async def test_runs_all_games(self, mock_session, mock_account):
        mock_result = {"success": True, "day": 1, "message": "OK"}
        with patch("src.api.checkin.do_checkin", new_callable=AsyncMock, return_value=mock_result):
            result = await run_checkin_for_account(mock_session, mock_account)

        assert len(result) == 3  # 3 games
        assert Game.GENSHIN in result
        assert Game.STAR_RAIL in result
        assert Game.ZZZ in result


# ==================== FETCH CDKEYS retcode != 0 ====================


class TestFetchCdkeysRetcode:
    @pytest.mark.asyncio
    async def test_retcode_not_zero(self, mock_session, mock_account):
        """fetch_cdkeys khi retcode != 0 → return []"""
        mock_resp = {"success": True, "data": {"retcode": -1, "message": "error"}}
        with patch("src.api.redeem_fetch.safe_api_call", return_value=mock_resp):
            result = await fetch_cdkeys(mock_session, mock_account, Game.GENSHIN)
        assert result == []


# ==================== DISPLAY TRUNCATION ====================


class TestDisplayTruncation:
    def test_long_status_truncated_in_table(self):
        """Status dài hơn column width bị cắt"""
        from src.utils.display import _short_redeem_status
        long_msg = {"success": False, "message": "A" * 100}
        status = _short_redeem_status(long_msg)
        # Status chứa đủ message ban đầu, truncation xảy ra trong display_redeem_results
        assert status.startswith("✗")

    def test_redeem_table_truncates_long_status(self):
        """display_redeem_results truncate status quá dài"""
        from src.utils.display import display_redeem_results
        results_map = {
            "ACC_1": {
                Game.ZZZ: {
                    "asia": {"CODE1": {"success": False, "message": "A" * 50}},
                }
            }
        }
        lines = []
        with patch("src.utils.display.log_print", side_effect=lambda m="": lines.append(m)):
            display_redeem_results(results_map)

        # Tìm dòng data chứa ".." (truncated)
        data_lines = [l for l in lines if "CODE1" in l or ".." in l]
        # Status phải bị truncate vì quá dài
        assert any(".." in l for l in data_lines)


# ==================== LOGGER ====================


class TestLogger:
    def test_log_error(self):
        """log_error ghi level ERROR"""
        from src.utils.logger import log_error
        with patch("src.utils.logger.logger") as mock_logger:
            log_error("ACC_1", "test error")
            mock_logger.error.assert_called_once()
            assert "ACC_1" in mock_logger.error.call_args[0][0]


# ==================== CHECKIN RETCODE PROPAGATION ====================


class TestCheckinRetcodePropagation:
    @pytest.mark.asyncio
    async def test_do_checkin_error_with_retcode(self, mock_session, mock_account):
        """do_checkin truyền retcode từ get_checkin_info khi có lỗi (cover checkin.py:110)"""
        info_with_retcode = {"is_sign": False, "total_sign_day": 0, "error": "No character", "retcode": -10002}
        with patch("src.api.checkin.get_checkin_info", return_value=info_with_retcode):
            result = await do_checkin(mock_session, mock_account, Game.ZZZ)
            assert result["success"] is False
            assert result["retcode"] == -10002

    @pytest.mark.asyncio
    async def test_do_checkin_error_without_retcode(self, mock_session, mock_account):
        """do_checkin khi info không có retcode (network error) → không set retcode"""
        info_no_retcode = {"is_sign": False, "total_sign_day": 0, "error": "timeout", "retcode": None}
        with patch("src.api.checkin.get_checkin_info", return_value=info_no_retcode):
            result = await do_checkin(mock_session, mock_account, Game.GENSHIN)
            assert result["success"] is False
            assert "retcode" not in result


# ==================== CLIENT ZERO RETRIES FALLBACK ====================


class TestSafeApiCallZeroRetries:
    @pytest.fixture(autouse=True)
    def _reset(self):
        reset_semaphore()
        yield
        reset_semaphore()

    @pytest.mark.asyncio
    async def test_max_retries_zero_returns_fallback(self, mock_session):
        """max_retries=0 → skip for loop → all-retries-exhausted fallback (cover client.py:166)"""
        with (
            patch("src.api.client.asyncio.sleep"),
            patch("src.api.client._get_semaphore"),
        ):
            result = await safe_api_call(mock_session, "http://test.com", {}, max_retries=0)
            assert result["success"] is False
            assert result["error"] == "max_retries"
            assert "Failed after 0 attempts" in result["message"]


# ==================== FETCH_APP_DATA EMPTY ACCOUNTS ====================


class TestFetchAppDataEmpty:
    @pytest.mark.asyncio
    async def test_empty_accounts_returns_empty(self, mock_session):
        """fetch_app_data([]) trả dict rỗng thay vì IndexError (cover main.py:73)"""
        from src.main import fetch_app_data

        cdkeys, account_uids = await fetch_app_data(mock_session, [])
        assert all(codes == [] for codes in cdkeys.values())
        assert account_uids == {}
