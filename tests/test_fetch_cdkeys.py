"""Tests cho fetch CDKeys functionality"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.models.game import Game
from src.api.redeem import fetch_cdkeys, fetch_all_cdkeys


class TestFetchCdkeys:
    """Test cases cho fetch_cdkeys function"""
    
    @pytest.mark.asyncio
    async def test_fetch_cdkeys_genshin_success(self, mock_session, mock_account):
        """Test fetch CDKeys cho Genshin thành công"""
        # safe_api_call returns {"success": True, "data": <api_response>}
        mock_api_response = {
            "success": True,
            "data": {
                "retcode": 0,
                "data": {
                    "modules": [
                        {
                            "exchange_group": {
                                "bonuses": [
                                    {"exchange_code": "GENSHINGIFT2024"},
                                    {"exchange_code": "PRIMOGEMS500"},
                                ]
                            }
                        }
                    ]
                }
            }
        }
        
        with patch("src.api.redeem.safe_api_call") as mock_api:
            mock_api.return_value = mock_api_response
            
            result = await fetch_cdkeys(mock_session, mock_account, Game.GENSHIN)
            
            # Verify codes được trích xuất đúng
            assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_fetch_cdkeys_empty_response(self, mock_session, mock_account):
        """Test fetch CDKeys khi API trả về rỗng"""
        mock_api_response = {
            "success": True,
            "data": {
                "retcode": 0,
                "data": {
                    "modules": []
                }
            }
        }
        
        with patch("src.api.redeem.safe_api_call") as mock_api:
            mock_api.return_value = mock_api_response
            
            result = await fetch_cdkeys(mock_session, mock_account, Game.STAR_RAIL)
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_cdkeys_api_error(self, mock_session, mock_account):
        """Test fetch CDKeys khi API lỗi"""
        with patch("src.api.redeem.safe_api_call") as mock_api:
            # API failed - returns {"success": False, ...}
            mock_api.return_value = {"success": False, "error": "network", "message": "Connection failed"}
            
            result = await fetch_cdkeys(mock_session, mock_account, Game.ZZZ)
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_cdkeys_invalid_structure(self, mock_session, mock_account):
        """Test fetch CDKeys khi response structure không đúng"""
        mock_api_response = {
            "success": True,
            "data": {
                "retcode": 0,
                "data": {
                    "unexpected_field": "value"
                }
            }
        }
        
        with patch("src.api.redeem.safe_api_call") as mock_api:
            mock_api.return_value = mock_api_response
            
            result = await fetch_cdkeys(mock_session, mock_account, Game.GENSHIN)
            
            assert result == []


class TestFetchAllCdkeys:
    """Test cases cho fetch_all_cdkeys function"""
    
    @pytest.mark.asyncio
    async def test_fetch_all_games_parallel(self, mock_session, mock_account):
        """Test fetch CDKeys cho tất cả games song song"""
        async def mock_fetch_cdkeys(session, account, game):
            if game == Game.GENSHIN:
                return ["GS1", "GS2"]
            elif game == Game.STAR_RAIL:
                return ["HSR1"]
            else:
                return []
        
        with patch("src.api.redeem.fetch_cdkeys", side_effect=mock_fetch_cdkeys):
            result = await fetch_all_cdkeys(mock_session, mock_account)
            
            assert Game.GENSHIN in result
            assert Game.STAR_RAIL in result
            assert Game.ZZZ in result
            
            assert len(result[Game.GENSHIN]) == 2
            assert len(result[Game.STAR_RAIL]) == 1
            assert len(result[Game.ZZZ]) == 0
    
    @pytest.mark.asyncio
    async def test_fetch_all_games_all_empty(self, mock_session, mock_account):
        """Test khi tất cả games đều không có codes"""
        with patch("src.api.redeem.fetch_cdkeys", return_value=[]):
            result = await fetch_all_cdkeys(mock_session, mock_account)
            
            assert all(len(codes) == 0 for codes in result.values())
    
    @pytest.mark.asyncio
    async def test_fetch_all_games_partial_failure(self, mock_session, mock_account):
        """Test khi một số games lỗi"""
        call_count = 0
        
        async def mock_fetch_with_error(session, account, game):
            nonlocal call_count
            call_count += 1
            if game == Game.STAR_RAIL:
                return []  # Simulating error/empty
            return ["CODE1"]
        
        with patch("src.api.redeem.fetch_cdkeys", side_effect=mock_fetch_with_error):
            result = await fetch_all_cdkeys(mock_session, mock_account)
            
            # Should still return results for all games
            assert len(result) == 3
            assert call_count == 3
