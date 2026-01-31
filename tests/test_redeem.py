"""Tests cho redeem functionality - exchange_cdkey và run_redeem"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiohttp import ClientResponseError

from src.models.game import Game
from src.api.redeem import (
    exchange_cdkey,
    redeem_codes_for_region,
    run_redeem_for_account,
)


class TestExchangeCdkey:
    """Test cases cho exchange_cdkey function"""
    
    @pytest.mark.asyncio
    async def test_exchange_success(self, mock_session, mock_account, mock_redeem_success):
        """Test redeem thành công"""
        # Mock response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_redeem_success)
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        with patch("src.api.redeem.safe_api_call") as mock_api:
            mock_api.return_value = mock_redeem_success
            
            result = await exchange_cdkey(
                mock_session,
                mock_account,
                Game.GENSHIN,
                "os_asia",
                "800000001",
                "GENSHINGIFT2024"
            )
            
            assert result["success"] is True
            assert "OK" in result["message"] or "thành công" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_exchange_already_claimed(self, mock_session, mock_account, mock_redeem_already_claimed):
        """Test code đã được redeem trước đó"""
        with patch("src.api.redeem.safe_api_call") as mock_api:
            mock_api.return_value = mock_redeem_already_claimed
            
            result = await exchange_cdkey(
                mock_session,
                mock_account,
                Game.GENSHIN,
                "os_asia",
                "800000001",
                "USEDCODE123"
            )
            
            # retcode -2017: Ưu tiên message từ API ("Redemption code has been used")
            assert "redemption code has been used" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_exchange_expired(self, mock_session, mock_account, mock_redeem_expired):
        """Test code đã hết hạn"""
        with patch("src.api.redeem.safe_api_call") as mock_api:
            mock_api.return_value = mock_redeem_expired
            
            result = await exchange_cdkey(
                mock_session,
                mock_account,
                Game.GENSHIN,
                "os_asia",
                "800000001",
                "EXPIREDCODE"
            )
            
            # retcode -2001: Ưu tiên message từ API ("Redemption code has expired")
            assert "redemption code has expired" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_exchange_invalid_code(self, mock_session, mock_account, mock_redeem_invalid):
        """Test code không hợp lệ"""
        with patch("src.api.redeem.safe_api_call") as mock_api:
            mock_api.return_value = mock_redeem_invalid
            
            result = await exchange_cdkey(
                mock_session,
                mock_account,
                Game.GENSHIN,
                "os_asia",
                "800000001",
                "INVALIDXXX"
            )
            
            # retcode -2003: Ưu tiên message từ API ("Invalid redemption code")
            assert "invalid redemption code" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_exchange_cooldown(self, mock_session, mock_account, mock_redeem_cooldown):
        """Test bị cooldown khi redeem quá nhanh"""
        with patch("src.api.redeem.safe_api_call") as mock_api:
            mock_api.return_value = mock_redeem_cooldown
            
            result = await exchange_cdkey(
                mock_session,
                mock_account,
                Game.STAR_RAIL,
                "prod_official_asia",
                "1300000001",
                "HSRGIFT2024"
            )
            
            # retcode -2016: Ưu tiên message từ API ("Redemption in cooldown")
            assert "redemption in cooldown" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_exchange_low_rank(self, mock_session, mock_account, mock_redeem_low_rank):
        """Test chưa đủ rank - retcode -2011"""
        with patch("src.api.redeem.safe_api_call") as mock_api:
            mock_api.return_value = mock_redeem_low_rank
            
            result = await exchange_cdkey(
                mock_session,
                mock_account,
                Game.GENSHIN,
                "os_asia",
                "800000001",
                "SOMECODE"
            )
            
            # retcode -2011: Ưu tiên message từ API ("You do not meet the Adventure Rank requirements")
            assert "adventure rank requirements" in result["message"].lower()
            # Should have skip_remaining flag
            assert result.get("skip_remaining") is True
    
    @pytest.mark.asyncio
    async def test_redeem_skip_on_low_rank(self, mock_session, mock_account, mock_redeem_low_rank):
        """Test redeem loop breaks early when -2011 returned"""
        codes = ["CODE1", "CODE2", "CODE3"]
        
        with patch("src.api.redeem.safe_api_call") as mock_api:
            mock_api.return_value = mock_redeem_low_rank
            
            with patch("src.api.redeem.asyncio.sleep"):
                result = await redeem_codes_for_region(
                    mock_session,
                    mock_account,
                    Game.GENSHIN,
                    "os_euro",
                    "700000001",
                    codes
                )
        
        # Should only have 1 result (loop broke after first code)
        assert len(result) == 1
        assert "CODE1" in result
        # CODE2 and CODE3 should NOT be in results
        assert "CODE2" not in result
        assert "CODE3" not in result

    @pytest.mark.asyncio
    async def test_exchange_fallback_translation(self, mock_session, mock_account):
        """Test fallback sang REDEEM_MESSAGES khi API không trả về message"""
        mock_response_no_msg = {
            "success": True,
            "data": {
                "retcode": -2017,
                # "message" is missing
                "data": None,
            }
        }
        with patch("src.api.redeem.safe_api_call") as mock_api:
            mock_api.return_value = mock_response_no_msg
            
            result = await exchange_cdkey(
                mock_session,
                mock_account,
                Game.ZZZ,
                "prod_gf_jp",
                "1000000001",
                "SOMECODE"
            )
            
            assert result["success"] is False
            # Nên lấy từ REDEEM_MESSAGES cho -2017
            assert "đã sử dụng hoặc không đủ điều kiện" in result["message"].lower()


class TestRedeemCodesForRegion:
    """Test cases cho redeem_codes_for_region function"""
    
    @pytest.mark.asyncio
    async def test_redeem_multiple_codes_success(self, mock_session, mock_account, mock_redeem_success):
        """Test redeem nhiều codes thành công"""
        codes = ["CODE1", "CODE2", "CODE3"]
        
        with patch("src.api.redeem.exchange_cdkey") as mock_exchange:
            mock_exchange.return_value = {"success": True, "message": "OK"}
            
            with patch("src.api.redeem.asyncio.sleep"):  # Skip delay
                result = await redeem_codes_for_region(
                    mock_session,
                    mock_account,
                    Game.GENSHIN,
                    "os_asia",
                    "800000001",
                    codes
                )
            
            assert len(result) == 3
            assert mock_exchange.call_count == 3
    
    @pytest.mark.asyncio
    async def test_redeem_empty_codes_list(self, mock_session, mock_account):
        """Test với list codes rỗng"""
        result = await redeem_codes_for_region(
            mock_session,
            mock_account,
            Game.GENSHIN,
            "os_asia",
            "800000001",
            []
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
        
        with patch("src.api.redeem.exchange_cdkey", side_effect=mock_exchange_side_effect):
            with patch("src.api.redeem.asyncio.sleep"):
                result = await redeem_codes_for_region(
                    mock_session,
                    mock_account,
                    Game.ZZZ,
                    "prod_gf_jp",
                    "1000000001",
                    codes
                )
        
        assert len(result) == 3
        assert result["SUCCESS"]["success"] is True
        assert result["USED"]["success"] is False
        assert result["EXPIRED"]["success"] is False


class TestRunRedeemForAccount:
    """Test cases cho run_redeem_for_account function"""
    
    @pytest.mark.asyncio
    async def test_redeem_all_games(
        self, 
        mock_session, 
        mock_account, 
        mock_cdkeys_all_games, 
        mock_uids_all_regions
    ):
        """Test redeem cho tất cả games với UIDs đầy đủ"""
        with patch("src.api.redeem.redeem_codes_for_region") as mock_redeem:
            mock_redeem.return_value = {"CODE1": {"success": True, "message": "OK"}}
            
            result = await run_redeem_for_account(
                mock_session,
                mock_account,
                mock_cdkeys_all_games,
                mock_uids_all_regions
            )
            
            # Phải gọi cho mỗi game × mỗi region có UID
            assert mock_redeem.call_count > 0
    
    @pytest.mark.asyncio
    async def test_redeem_no_codes(
        self, 
        mock_session, 
        mock_account, 
        mock_cdkeys_empty, 
        mock_uids_all_regions
    ):
        """Test khi không có codes nào"""
        with patch("src.api.redeem.redeem_codes_for_region") as mock_redeem:
            result = await run_redeem_for_account(
                mock_session,
                mock_account,
                mock_cdkeys_empty,
                mock_uids_all_regions
            )
            
            # Không nên gọi redeem khi không có codes
            assert mock_redeem.call_count == 0
    
    @pytest.mark.asyncio
    async def test_redeem_no_uids(
        self, 
        mock_session, 
        mock_account, 
        mock_cdkeys_all_games, 
        mock_uids_empty
    ):
        """Test khi không có UIDs (chưa tạo nhân vật)"""
        with patch("src.api.redeem.redeem_codes_for_region") as mock_redeem:
            result = await run_redeem_for_account(
                mock_session,
                mock_account,
                mock_cdkeys_all_games,
                mock_uids_empty
            )
            
            # Không nên gọi redeem khi không có UIDs
            assert mock_redeem.call_count == 0
    
    @pytest.mark.asyncio
    async def test_redeem_partial_games(
        self, 
        mock_session, 
        mock_account, 
        mock_cdkeys_partial, 
        mock_uids_partial
    ):
        """Test với chỉ một số games có codes và UIDs"""
        with patch("src.api.redeem.redeem_codes_for_region") as mock_redeem:
            mock_redeem.return_value = {"CODE": {"success": True, "message": "OK"}}
            
            result = await run_redeem_for_account(
                mock_session,
                mock_account,
                mock_cdkeys_partial,
                mock_uids_partial
            )
            
            # Chỉ redeem cho games có cả codes VÀ UIDs
            # GENSHIN: có 1 code, có 1 UID → gọi 1 lần
            # STARRAIL: không có codes → không gọi
            # ZZZ: có 2 codes, có 2 UIDs → gọi 2 lần
            assert mock_redeem.call_count == 3  # 1 + 0 + 2
