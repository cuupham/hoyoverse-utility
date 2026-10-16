"""Tests cho redeem functionality - exchange_cdkey và run_redeem"""

from unittest.mock import patch

import pytest

from src.api.redeem_exchange import (
    _redeem_game_for_account,
    exchange_cdkey,
    redeem_codes_for_region,
    run_redeem_for_account,
)
from src.models.game import Game


class TestExchangeCdkey:
    """Test cases cho exchange_cdkey function"""

    @pytest.mark.asyncio
    async def test_exchange_success(
        self, mock_session, mock_account, mock_redeem_success
    ):
        """Test redeem thành công"""
        with patch("src.api.redeem_exchange.request_json") as mock_api:
            mock_api.return_value = mock_redeem_success

            result = await exchange_cdkey(
                mock_session,
                mock_account,
                Game.GENSHIN,
                "asia",
                "800000001",
                "GENSHINGIFT2024",
            )

            assert result["success"] is True
            assert (
                "OK" in result["message"] or "thành công" in result["message"].lower()
            )

    @pytest.mark.asyncio
    async def test_exchange_preserves_rejection_2017(
        self, mock_session, mock_account, mock_redeem_rejection_2017
    ):
        """Test code đã được redeem trước đó"""
        with patch("src.api.redeem_exchange.request_json") as mock_api:
            mock_api.return_value = mock_redeem_rejection_2017

            result = await exchange_cdkey(
                mock_session,
                mock_account,
                Game.GENSHIN,
                "asia",
                "800000001",
                "USEDCODE123",
            )

            # Preserve the provider message for -2017
            assert result["message"] == mock_redeem_rejection_2017["data"]["message"]

    @pytest.mark.asyncio
    async def test_exchange_preserves_rejection_2001(
        self, mock_session, mock_account, mock_redeem_rejection_2001
    ):
        """Preserve the message and retcode from the provider"""
        with patch("src.api.redeem_exchange.request_json") as mock_api:
            mock_api.return_value = mock_redeem_rejection_2001

            result = await exchange_cdkey(
                mock_session,
                mock_account,
                Game.GENSHIN,
                "asia",
                "800000001",
                "EXPIREDCODE",
            )

            assert result["message"] == mock_redeem_rejection_2001["data"]["message"]

    @pytest.mark.asyncio
    async def test_exchange_preserves_rejection_2003(
        self, mock_session, mock_account, mock_redeem_rejection_2003
    ):
        """Test code không hợp lệ (retcode -2003)"""
        with patch("src.api.redeem_exchange.request_json") as mock_api:
            mock_api.return_value = mock_redeem_rejection_2003

            result = await exchange_cdkey(
                mock_session,
                mock_account,
                Game.GENSHIN,
                "asia",
                "800000001",
                "INVALIDXXX",
            )

            assert result["message"] == mock_redeem_rejection_2003["data"]["message"]

    @pytest.mark.asyncio
    async def test_exchange_preserves_rejection_2016(
        self, mock_session, mock_account, mock_redeem_rejection_2016
    ):
        """Preserve -2016 without assuming permanent expiry"""
        with patch("src.api.redeem_exchange.request_json") as mock_api:
            mock_api.return_value = mock_redeem_rejection_2016

            result = await exchange_cdkey(
                mock_session,
                mock_account,
                Game.STAR_RAIL,
                "asia",
                "1300000001",
                "HSRGIFT2024",
            )

            assert result["message"] == mock_redeem_rejection_2016["data"]["message"]

    @pytest.mark.asyncio
    async def test_exchange_preserves_rejection_2011(
        self, mock_session, mock_account, mock_redeem_rejection_2011
    ):
        """Test chưa đủ rank - retcode -2011"""
        with patch("src.api.redeem_exchange.request_json") as mock_api:
            mock_api.return_value = mock_redeem_rejection_2011

            result = await exchange_cdkey(
                mock_session,
                mock_account,
                Game.GENSHIN,
                "asia",
                "800000001",
                "SOMECODE",
            )

            assert result["message"] == mock_redeem_rejection_2011["data"]["message"]
            assert result["error_kind"] == "provider"

    @pytest.mark.asyncio
    async def test_redeem_continues_after_code_rank_rejection(
        self, mock_session, mock_account, mock_redeem_rejection_2011
    ):
        """One code rank rejection must not suppress unrelated codes"""
        codes = ["CODE1", "CODE2", "CODE3"]

        with (
            patch("src.api.redeem_exchange.request_json") as mock_api,
            patch("src.api.redeem_exchange.asyncio.sleep"),
        ):
            mock_api.return_value = mock_redeem_rejection_2011
            result = await redeem_codes_for_region(
                mock_session, mock_account, Game.GENSHIN, "euro", "700000001", codes
            )

        assert set(result) == set(codes)
        assert mock_api.await_count == 3

    @pytest.mark.asyncio
    async def test_exchange_fallback_to_numeric_error(self, mock_session, mock_account):
        """Missing messages fall back to the numeric error"""
        mock_response_no_msg = {
            "success": True,
            "data": {
                "retcode": -2017,
                "data": None,
            },
        }
        with patch("src.api.redeem_exchange.request_json") as mock_api:
            mock_api.return_value = mock_response_no_msg

            result = await exchange_cdkey(
                mock_session, mock_account, Game.ZZZ, "asia", "1000000001", "SOMECODE"
            )

            assert result["success"] is False
            assert result["message"] == "Error -2017"


class TestRedeemCodesForRegion:
    """Test cases cho redeem_codes_for_region function"""

    @pytest.mark.asyncio
    async def test_redeem_multiple_codes_success(
        self, mock_session, mock_account, mock_redeem_success
    ):
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
        result = await redeem_codes_for_region(
            mock_session, mock_account, Game.GENSHIN, "asia", "800000001", []
        )
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
            patch(
                "src.api.redeem_exchange.exchange_cdkey",
                side_effect=mock_exchange_side_effect,
            ),
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
    async def test_redeem_all_games(
        self, mock_session, mock_account, mock_cdkeys_all_games, mock_uids_all_regions
    ):
        """Test redeem cho tất cả games với UIDs đầy đủ"""
        with patch("src.api.redeem_exchange.redeem_codes_for_region") as mock_redeem:
            mock_redeem.return_value = {"CODE1": {"success": True, "message": "OK"}}

            result = await run_redeem_for_account(
                mock_session, mock_account, mock_cdkeys_all_games, mock_uids_all_regions
            )

            assert set(result) == set(Game)
            assert all(
                set(result[game]) == set(mock_uids_all_regions[game]) for game in Game
            )
            assert all(
                codes["CODE1"]["success"]
                for regions in result.values()
                for codes in regions.values()
            )
            assert mock_redeem.call_count == 12

    @pytest.mark.asyncio
    async def test_redeem_no_codes(
        self, mock_session, mock_account, mock_cdkeys_empty, mock_uids_all_regions
    ):
        """Test khi không có codes nào"""
        with patch("src.api.redeem_exchange.redeem_codes_for_region") as mock_redeem:
            result = await run_redeem_for_account(
                mock_session, mock_account, mock_cdkeys_empty, mock_uids_all_regions
            )
            assert result == {}
            assert mock_redeem.call_count == 0

    @pytest.mark.asyncio
    async def test_redeem_no_uids(
        self, mock_session, mock_account, mock_cdkeys_all_games, mock_uids_empty
    ):
        """Test khi không có UIDs (chưa tạo nhân vật)"""
        with patch("src.api.redeem_exchange.redeem_codes_for_region") as mock_redeem:
            result = await run_redeem_for_account(
                mock_session, mock_account, mock_cdkeys_all_games, mock_uids_empty
            )
            assert result == {}
            assert mock_redeem.call_count == 0

    @pytest.mark.asyncio
    async def test_redeem_partial_games(
        self, mock_session, mock_account, mock_cdkeys_partial, mock_uids_partial
    ):
        """Test với chỉ một số games có codes và UIDs"""
        with patch("src.api.redeem_exchange.redeem_codes_for_region") as mock_redeem:
            mock_redeem.return_value = {"CODE": {"success": True, "message": "OK"}}

            result = await run_redeem_for_account(
                mock_session, mock_account, mock_cdkeys_partial, mock_uids_partial
            )

            # GENSHIN: 1 code, 1 UID → 1 call; SR: 0; ZZZ: 2 codes, 2 UIDs → 2 calls
            assert set(result) == {Game.GENSHIN, Game.ZZZ}
            assert set(result[Game.GENSHIN]) == {"asia"}
            assert set(result[Game.ZZZ]) == {"asia", "usa"}
            assert all(
                codes["CODE"]["success"]
                for regions in result.values()
                for codes in regions.values()
            )
            assert mock_redeem.call_count == 3


class TestRedeemEdgeCases:
    @pytest.mark.asyncio
    async def test_exchange_unknown_region(self, mock_session, mock_account):
        result = await exchange_cdkey(
            mock_session, mock_account, Game.GENSHIN, "mars", "123", "CODE"
        )
        assert result["success"] is False
        assert "Unknown region" in result["message"]

    @pytest.mark.asyncio
    async def test_exchange_api_failure(self, mock_session, mock_account):
        with patch(
            "src.api.redeem_exchange.request_json",
            return_value={"success": False, "message": "timeout"},
        ):
            result = await exchange_cdkey(
                mock_session, mock_account, Game.GENSHIN, "asia", "800001", "CODE"
            )
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_exchange_unknown_retcode_fallback(self, mock_session, mock_account):
        """Unknown provider retcode preserves the provider message"""
        mock_resp = {
            "success": True,
            "data": {"retcode": -9999, "message": "Unknown API error"},
        }
        with patch("src.api.redeem_exchange.request_json", return_value=mock_resp):
            result = await exchange_cdkey(
                mock_session, mock_account, Game.GENSHIN, "asia", "800001", "CODE"
            )
            assert result["message"] == "Unknown API error"

    @pytest.mark.asyncio
    async def test_exchange_no_message_no_mapping(self, mock_session, mock_account):
        """Missing provider message falls back to the numeric retcode"""
        mock_resp = {"success": True, "data": {"retcode": -9999}}
        with patch("src.api.redeem_exchange.request_json", return_value=mock_resp):
            result = await exchange_cdkey(
                mock_session, mock_account, Game.GENSHIN, "asia", "800001", "CODE"
            )
            assert "Error -9999" in result["message"]

    @pytest.mark.asyncio
    async def test_provider_rejection_does_not_suppress_next_region(
        self, mock_session, mock_account
    ):
        codes = ["GLOBAL_EXPIRED"]
        uids = {"asia": "800", "usa": "600"}

        with (
            patch("src.api.redeem_exchange.exchange_cdkey") as mock_exchange,
            patch("src.api.redeem_exchange.asyncio.sleep"),
        ):
            mock_exchange.return_value = {
                "success": False,
                "message": "Expired",
                "retcode": -2001,
            }
            results = await _redeem_game_for_account(
                mock_session, mock_account, Game.GENSHIN, codes, uids
            )

        assert mock_exchange.call_count == 2
        assert results["usa"]["GLOBAL_EXPIRED"]["success"] is False
