"""Tests cho check-in functionality"""

from unittest.mock import AsyncMock, patch

import pytest

from src.api.checkin import (
    check_cookie,
    do_checkin,
    get_checkin_info,
    run_checkin_for_account,
)
from src.models.game import Game


class TestCheckCookie:
    """Test cases cho check_cookie function"""

    @pytest.mark.asyncio
    async def test_check_cookie_success(
        self, mock_session, mock_account, mock_check_cookie_success
    ):
        """Test cookie hợp lệ"""
        with patch("src.api.checkin.request_json") as mock_api:
            mock_api.return_value = mock_check_cookie_success

            result = await check_cookie(mock_session, mock_account)

            assert result["valid"] is True
            assert result["email_mask"] == "a****x1234@example.com"
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_check_cookie_invalid(
        self, mock_session, mock_account, mock_check_cookie_invalid
    ):
        """Test cookie hết hạn"""
        with patch("src.api.checkin.request_json") as mock_api:
            mock_api.return_value = mock_check_cookie_invalid

            result = await check_cookie(mock_session, mock_account)

            assert result["valid"] is False
            assert result["email_mask"] is None
            assert "login" in result["error"].lower()


class TestGetCheckinInfo:
    """Test cases cho get_checkin_info function"""

    @pytest.mark.asyncio
    async def test_get_checkin_info_gs(
        self, mock_session, mock_account, mock_checkin_info_not_signed
    ):
        """Test lấy info cho Genshin Impact (Sol)"""
        with patch("src.api.checkin.request_json") as mock_api:
            mock_api.return_value = mock_checkin_info_not_signed

            result = await get_checkin_info(mock_session, mock_account, Game.GENSHIN)

            assert result["is_sign"] is False
            assert result["total_sign_day"] == 10

            # Verify headers (Sol)
            args, _ = mock_api.call_args
            headers = args[2]
            assert "x-rpc-lrsag" in headers
            assert headers["x-rpc-signgame"] == "hk4e"

    @pytest.mark.asyncio
    async def test_get_checkin_info_sr(
        self, mock_session, mock_account, mock_checkin_info_signed
    ):
        """Test lấy info cho Star Rail (Luna)"""
        with patch("src.api.checkin.request_json") as mock_api:
            mock_api.return_value = mock_checkin_info_signed

            result = await get_checkin_info(mock_session, mock_account, Game.STAR_RAIL)

            assert result["is_sign"] is True
            assert result["total_sign_day"] == 11

            # Verify headers (Luna)
            args, _ = mock_api.call_args
            headers = args[2]
            assert "x-rpc-signgame" in headers
            assert headers["x-rpc-signgame"] == "hkrpg"


class TestDoCheckin:
    """Test cases cho do_checkin function"""

    @pytest.mark.asyncio
    async def test_do_checkin_success(
        self, mock_session, mock_account, mock_checkin_sign_success
    ):
        """Test điểm danh thành công"""
        not_signed = {"is_sign": False, "total_sign_day": 10, "error": None}

        with (
            patch(
                "src.api.checkin.get_checkin_info", return_value=not_signed
            ) as mock_get_info,
            patch(
                "src.api.checkin.request_json", return_value=mock_checkin_sign_success
            ),
        ):
            result = await do_checkin(mock_session, mock_account, Game.GENSHIN)

            mock_get_info.assert_called_once()  # chỉ gọi 1 lần, increment local
            assert result["success"] is True
            assert result["day"] == 11  # 10 + 1 (local increment)
            assert "thành công" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_do_checkin_already_signed(self, mock_session, mock_account):
        """Test trường hợp đã điểm danh rồi"""
        signed_processed = {"is_sign": True, "total_sign_day": 11, "error": None}
        with patch("src.api.checkin.get_checkin_info") as mock_get_info:
            mock_get_info.return_value = signed_processed

            result = await do_checkin(mock_session, mock_account, Game.GENSHIN)

            assert result["success"] is True
            assert result["day"] == 11
            assert "trước đó" in result["message"]

    @pytest.mark.asyncio
    async def test_do_checkin_no_character(
        self, mock_session, mock_account, mock_checkin_no_character
    ):
        """Test trường hợp không có nhân vật"""
        with patch("src.api.checkin.get_checkin_info") as mock_get_info:
            mock_get_info.return_value = {
                "is_sign": False,
                "total_sign_day": 0,
                "error": "No in-game character",
            }

            result = await do_checkin(mock_session, mock_account, Game.GENSHIN)

            assert result["success"] is False
            assert "character" in result["message"]


class TestCheckinFailPaths:
    @pytest.mark.asyncio
    async def test_check_cookie_api_failure(self, mock_session, mock_account):
        """check_cookie khi API call fail"""
        with patch(
            "src.api.checkin.request_json",
            return_value={"success": False, "message": "timeout"},
        ):
            result = await check_cookie(mock_session, mock_account)
            assert result["valid"] is False
            assert "timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_get_checkin_info_api_failure(self, mock_session, mock_account):
        """get_checkin_info khi API call fail"""
        with patch(
            "src.api.checkin.request_json",
            return_value={"success": False, "message": "network"},
        ):
            result = await get_checkin_info(mock_session, mock_account, Game.GENSHIN)
            assert result["error"] == "network"
            assert result["is_sign"] is False

    @pytest.mark.asyncio
    async def test_get_checkin_info_retcode_not_zero(self, mock_session, mock_account):
        """get_checkin_info khi retcode != 0"""
        mock_resp = {
            "success": True,
            "data": {"retcode": -10002, "message": "No character"},
        }
        with patch("src.api.checkin.request_json", return_value=mock_resp):
            result = await get_checkin_info(mock_session, mock_account, Game.ZZZ)
            assert result["error"] == "No character"

    @pytest.mark.asyncio
    async def test_do_checkin_sign_post_fail(self, mock_session, mock_account):
        """do_checkin khi sign POST thất bại"""
        not_signed = {"is_sign": False, "total_sign_day": 5, "error": None}
        with (
            patch("src.api.checkin.get_checkin_info", return_value=not_signed),
            patch(
                "src.api.checkin.request_json",
                return_value={"success": False, "message": "timeout"},
            ),
        ):
            result = await do_checkin(mock_session, mock_account, Game.STAR_RAIL)
            assert result["success"] is False
            assert "timeout" in result["message"]

    @pytest.mark.asyncio
    async def test_do_checkin_sign_retcode_not_zero(self, mock_session, mock_account):
        """do_checkin khi sign POST trả retcode != 0"""
        not_signed = {"is_sign": False, "total_sign_day": 5, "error": None}
        sign_fail = {
            "success": True,
            "data": {"retcode": -1, "message": "Server error"},
        }
        with (
            patch("src.api.checkin.get_checkin_info", return_value=not_signed),
            patch("src.api.checkin.request_json", return_value=sign_fail),
        ):
            result = await do_checkin(mock_session, mock_account, Game.ZZZ)
            assert result["success"] is False
            assert "Server error" in result["message"]


class TestRunCheckinForAccount:
    @pytest.mark.asyncio
    async def test_runs_all_games(self, mock_session, mock_account):
        mock_result = {"success": True, "day": 1, "message": "OK"}
        with patch(
            "src.api.checkin.do_checkin",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await run_checkin_for_account(mock_session, mock_account)

        assert len(result) == 3  # 3 games
        assert Game.GENSHIN in result
        assert Game.STAR_RAIL in result
        assert Game.ZZZ in result


class TestCheckinRetcodePropagation:
    @pytest.mark.asyncio
    async def test_do_checkin_error_with_retcode(self, mock_session, mock_account):
        """do_checkin truyền retcode từ get_checkin_info khi có lỗi (cover checkin.py:110)"""
        info_with_retcode = {
            "is_sign": False,
            "total_sign_day": 0,
            "error": "No character",
            "retcode": -10002,
        }
        with patch("src.api.checkin.get_checkin_info", return_value=info_with_retcode):
            result = await do_checkin(mock_session, mock_account, Game.ZZZ)
            assert result["success"] is False
            assert result["retcode"] == -10002

    @pytest.mark.asyncio
    async def test_do_checkin_error_without_retcode(self, mock_session, mock_account):
        """do_checkin khi info không có retcode (network error) → không set retcode"""
        info_no_retcode = {
            "is_sign": False,
            "total_sign_day": 0,
            "error": "timeout",
            "retcode": None,
        }
        with patch("src.api.checkin.get_checkin_info", return_value=info_no_retcode):
            result = await do_checkin(mock_session, mock_account, Game.GENSHIN)
            assert result["success"] is False
            assert "retcode" not in result
