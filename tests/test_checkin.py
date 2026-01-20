"""Tests cho check-in functionality"""
import pytest
from unittest.mock import patch

from src.models.game import Game
from src.api.checkin import check_cookie, get_checkin_info, do_checkin


class TestCheckCookie:
    """Test cases cho check_cookie function"""
    
    @pytest.mark.asyncio
    async def test_check_cookie_success(self, mock_session, mock_account, mock_check_cookie_success):
        """Test cookie hợp lệ"""
        with patch("src.api.checkin.safe_api_call") as mock_api:
            mock_api.return_value = mock_check_cookie_success
            
            result = await check_cookie(mock_session, mock_account)
            
            assert result["valid"] is True
            assert result["email_mask"] == "c****u9991@gmail.com"
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_check_cookie_invalid(self, mock_session, mock_account, mock_check_cookie_invalid):
        """Test cookie hết hạn"""
        with patch("src.api.checkin.safe_api_call") as mock_api:
            mock_api.return_value = mock_check_cookie_invalid
            
            result = await check_cookie(mock_session, mock_account)
            
            assert result["valid"] is False
            assert result["email_mask"] is None
            assert "login" in result["error"].lower()


class TestGetCheckinInfo:
    """Test cases cho get_checkin_info function"""
    
    @pytest.mark.asyncio
    async def test_get_checkin_info_gs(self, mock_session, mock_account, mock_checkin_info_not_signed):
        """Test lấy info cho Genshin Impact (Sol)"""
        with patch("src.api.checkin.safe_api_call") as mock_api:
            mock_api.return_value = mock_checkin_info_not_signed
            
            result = await get_checkin_info(mock_session, mock_account, Game.GENSHIN)
            
            assert result["is_sign"] is False
            assert result["total_sign_day"] == 10
            
            # Verify headers (Sol)
            args, _ = mock_api.call_args
            headers = args[2]
            assert "x-rpc-lrsag" in headers
            assert "x-rpc-signgame" not in headers

    @pytest.mark.asyncio
    async def test_get_checkin_info_sr(self, mock_session, mock_account, mock_checkin_info_signed):
        """Test lấy info cho Star Rail (Luna)"""
        with patch("src.api.checkin.safe_api_call") as mock_api:
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
    async def test_do_checkin_success(self, mock_session, mock_account, mock_checkin_sign_success):
        """Test điểm danh thành công"""
        # mock_checkin_info_not_signed format correct for safe_api_call mock
        not_signed_processed = {"is_sign": False, "total_sign_day": 10, "error": None}
        signed_processed = {"is_sign": True, "total_sign_day": 11, "error": None}
        
        with patch("src.api.checkin.get_checkin_info") as mock_get_info:
            mock_get_info.side_effect = [not_signed_processed, signed_processed]
            
            with patch("src.api.checkin.safe_api_call") as mock_api:
                mock_api.return_value = mock_checkin_sign_success
                
                result = await do_checkin(mock_session, mock_account, Game.GENSHIN)
                
                assert result["success"] is True
                assert result["day"] == 11
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
    async def test_do_checkin_no_character(self, mock_session, mock_account, mock_checkin_no_character):
        """Test trường hợp không có nhân vật"""
        with patch("src.api.checkin.get_checkin_info") as mock_get_info:
            mock_get_info.return_value = {"is_sign": False, "total_sign_day": 0, "error": "No in-game character"}
            
            result = await do_checkin(mock_session, mock_account, Game.GENSHIN)
            
            assert result["success"] is False
            assert "character" in result["message"]
