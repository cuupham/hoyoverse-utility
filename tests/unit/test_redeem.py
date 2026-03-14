"""Tests cho redeem functionality - exchange_cdkey và run_redeem"""

import pytest
from unittest.mock import patch

from src.models.game import Game
from src.api.redeem_exchange import (
    exchange_cdkey,
    redeem_codes_for_region,
    run_redeem_for_account,
)


class TestExchangeCdkey:
    """Test cases cho exchange_cdkey function"""

    @pytest.mark.asyncio
    async def test_exchange_success(self, mock_session, mock_account, mock_redeem_success):
        """Test redeem thành công"""
        with patch("src.api.redeem_exchange.safe_api_call") as mock_api:
            mock_api.return_value = mock_redeem_success

            result = await exchange_cdkey(
                mock_session, mock_account, Game.GENSHIN, "asia", "800000001", "GENSHINGIFT2024"
            )

            assert result["success"] is True
            assert "OK" in result["message"] or "thành công" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_exchange_already_claimed(self, mock_session, mock_account, mock_redeem_already_claimed):
        """Test code đã được redeem trước đó"""
        with patch("src.api.redeem_exchange.safe_api_call") as mock_api:
            mock_api.return_value = mock_redeem_already_claimed

            result = await exchange_cdkey(mock_session, mock_account, Game.GENSHIN, "asia", "800000001", "USEDCODE123")

            # retcode -2017 → REDEEM_MESSAGES Vietnamese
            assert "đã sử dụng" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_exchange_nonexistent(self, mock_session, mock_account, mock_redeem_expired):
        """Test code không tồn tại (retcode -2001 = SKIP_GLOBALLY)"""
        with patch("src.api.redeem_exchange.safe_api_call") as mock_api:
            mock_api.return_value = mock_redeem_expired

            result = await exchange_cdkey(mock_session, mock_account, Game.GENSHIN, "asia", "800000001", "EXPIREDCODE")

            assert "không tồn tại" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_exchange_invalid_code(self, mock_session, mock_account, mock_redeem_invalid):
        """Test code không hợp lệ (retcode -2003)"""
        with patch("src.api.redeem_exchange.safe_api_call") as mock_api:
            mock_api.return_value = mock_redeem_invalid

            result = await exchange_cdkey(mock_session, mock_account, Game.GENSHIN, "asia", "800000001", "INVALIDXXX")

            assert "đã sử dụng" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_exchange_code_expired(self, mock_session, mock_account, mock_redeem_code_expired):
        """Test code đã hết hạn (retcode -2016 = SKIP_GLOBALLY)"""
        with patch("src.api.redeem_exchange.safe_api_call") as mock_api:
            mock_api.return_value = mock_redeem_code_expired

            result = await exchange_cdkey(
                mock_session, mock_account, Game.STAR_RAIL, "asia", "1300000001", "HSRGIFT2024"
            )

            assert "hết hạn" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_exchange_low_rank(self, mock_session, mock_account, mock_redeem_low_rank):
        """Test chưa đủ rank - retcode -2011"""
        with patch("src.api.redeem_exchange.safe_api_call") as mock_api:
            mock_api.return_value = mock_redeem_low_rank

            result = await exchange_cdkey(mock_session, mock_account, Game.GENSHIN, "asia", "800000001", "SOMECODE")

            assert "rank" in result["message"].lower()
            assert result.get("skip_remaining") is True

    @pytest.mark.asyncio
    async def test_redeem_skip_on_low_rank(self, mock_session, mock_account, mock_redeem_low_rank):
        """Test redeem loop breaks early when -2011 returned"""
        codes = ["CODE1", "CODE2", "CODE3"]

        with (
            patch("src.api.redeem_exchange.safe_api_call") as mock_api,
            patch("src.api.redeem_exchange.asyncio.sleep"),
        ):
            mock_api.return_value = mock_redeem_low_rank
            result = await redeem_codes_for_region(
                mock_session, mock_account, Game.GENSHIN, "euro", "700000001", codes
            )

        assert len(result) == 1
        assert "CODE1" in result
        assert "CODE2" not in result
        assert "CODE3" not in result

    @pytest.mark.asyncio
    async def test_exchange_fallback_translation(self, mock_session, mock_account):
        """Test fallback sang REDEEM_MESSAGES khi API không trả về message"""
        mock_response_no_msg = {
            "success": True,
            "data": {
                "retcode": -2017,
                "data": None,
            },
        }
        with patch("src.api.redeem_exchange.safe_api_call") as mock_api:
            mock_api.return_value = mock_response_no_msg

            result = await exchange_cdkey(mock_session, mock_account, Game.ZZZ, "asia", "1000000001", "SOMECODE")

            assert result["success"] is False
            assert "đã sử dụng" in result["message"].lower()


class TestRedeemCodesForRegion:
    """Test cases cho redeem_codes_for_region function"""

    @pytest.mark.asyncio
    async def test_redeem_multiple_codes_success(self, mock_session, mock_account, mock_redeem_success):
        """Test redeem nhiều codes thành công"""
        codes = ["CODE1", "CODE2", "CODE3"]

        with (
            patch("src.api.redeem_exchange.exchange_cdkey") as mock_exchange,
            patch("src.api.redeem_exchange.asyncio.sleep"),
        ):
            mock_exchange.return_value = {"success": True, "message": "OK"}
            result = await redeem_codes_for_region(
                mock_session, mock_account, Game.GENSHIN, "asia", "800000001", codes
            )

        assert len(result) == 3
        assert mock_exchange.call_count == 3

    @pytest.mark.asyncio
    async def test_redeem_empty_codes_list(self, mock_session, mock_account):
        """Test với list codes rỗng"""
        result = await redeem_codes_for_region(mock_session, mock_account, Game.GENSHIN, "asia", "800000001", [])
        assert result == {}

    @pytest.mark.asyncio
    async def test_redeem_mixed_results(self, mock_session, mock_account):
        """Test với mix kết quả: thành công, đã dùng, hết hạn"""
        codes = ["SUCCESS", "USED", "EXPIRED"]

        async def mock_exchange_side_effect(session, acc, game, region, uid, code):
            if code == "SUCCESS":
                return {"success": True, "message": "OK"}
            elif code == "USED":
                return {"success": False, "message": "Already claimed"}
            else:
                return {"success": False, "message": "Expired"}

        with (
            patch("src.api.redeem_exchange.exchange_cdkey", side_effect=mock_exchange_side_effect),
            patch("src.api.redeem_exchange.asyncio.sleep"),
        ):
            result = await redeem_codes_for_region(
                mock_session, mock_account, Game.ZZZ, "asia", "1000000001", codes
            )

        assert len(result) == 3
        assert result["SUCCESS"]["success"] is True
        assert result["USED"]["success"] is False
        assert result["EXPIRED"]["success"] is False


class TestRunRedeemForAccount:
    """Test cases cho run_redeem_for_account function"""

    @pytest.mark.asyncio
    async def test_redeem_all_games(self, mock_session, mock_account, mock_cdkeys_all_games, mock_uids_all_regions):
        """Test redeem cho tất cả games với UIDs đầy đủ"""
        with patch("src.api.redeem_exchange.redeem_codes_for_region") as mock_redeem:
            mock_redeem.return_value = {"CODE1": {"success": True, "message": "OK"}}

            result = await run_redeem_for_account(
                mock_session, mock_account, mock_cdkeys_all_games, mock_uids_all_regions
            )

            assert mock_redeem.call_count > 0

    @pytest.mark.asyncio
    async def test_redeem_no_codes(self, mock_session, mock_account, mock_cdkeys_empty, mock_uids_all_regions):
        """Test khi không có codes nào"""
        with patch("src.api.redeem_exchange.redeem_codes_for_region") as mock_redeem:
            result = await run_redeem_for_account(mock_session, mock_account, mock_cdkeys_empty, mock_uids_all_regions)
            assert mock_redeem.call_count == 0

    @pytest.mark.asyncio
    async def test_redeem_no_uids(self, mock_session, mock_account, mock_cdkeys_all_games, mock_uids_empty):
        """Test khi không có UIDs (chưa tạo nhân vật)"""
        with patch("src.api.redeem_exchange.redeem_codes_for_region") as mock_redeem:
            result = await run_redeem_for_account(mock_session, mock_account, mock_cdkeys_all_games, mock_uids_empty)
            assert mock_redeem.call_count == 0

    @pytest.mark.asyncio
    async def test_redeem_partial_games(self, mock_session, mock_account, mock_cdkeys_partial, mock_uids_partial):
        """Test với chỉ một số games có codes và UIDs"""
        with patch("src.api.redeem_exchange.redeem_codes_for_region") as mock_redeem:
            mock_redeem.return_value = {"CODE": {"success": True, "message": "OK"}}

            result = await run_redeem_for_account(mock_session, mock_account, mock_cdkeys_partial, mock_uids_partial)

            # GENSHIN: 1 code, 1 UID → 1 call; SR: 0; ZZZ: 2 codes, 2 UIDs → 2 calls
            assert mock_redeem.call_count == 3
