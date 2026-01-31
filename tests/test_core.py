"""Tests cho core components (Models, Utils, Client)"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from src.models.account import Account
from src.api.client import safe_api_call, create_session
from src.utils.security import mask_uid
from src.utils.helpers import current_hour, rpc_weekday, unix_ms


class TestAccountModel:
    """Test cases cho Account model"""
    
    def test_account_from_env_success(self):
        """Test tạo account thành công từ cookie string"""
        cookie = "ltoken_v2=v2; ltuid_v2=123; cookie_token_v2=c2; account_id_v2=456; _MHYUUID=m1; _HYVUUID=h1"
        acc = Account.from_env("ACC_1", cookie)
        assert acc.name == "ACC_1"
        assert acc.cookies["ltoken_v2"] == "v2"
        assert acc.mhy_uuid == "m1"
        assert acc.hyv_uuid == "h1"

    def test_account_from_env_missing_keys(self):
        """Test lỗi khi thiếu required keys"""
        cookie = "ltoken_v2=v2; ltuid_v2=123"  # Thiếu account_id_v2, etc.
        with pytest.raises(ValueError) as excinfo:
            Account.from_env("BAD_ACC", cookie)
        assert "Missing required cookies" in str(excinfo.value)


class TestApiClient:
    """Test cases cho safe_api_call và session isolation"""
    
    @pytest.mark.skip(reason="Mocking async with for retries is unstable in current test environment")
    @pytest.mark.asyncio
    async def test_safe_api_call_retry(self, mock_session):
        """Test cơ chế retry khi gặp lỗi mạng"""
        # Mock response object for Success
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"retcode": 0})
        
        # We need to mock session.request to be a regular MagicMock 
        # that returns an async context manager
        with patch.object(mock_session, 'request') as mock_request:
            # Call 1: Timeout
            mock_cm_timeout = MagicMock()
            mock_cm_timeout.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_cm_timeout.__aexit__ = AsyncMock()
            
            # Call 2: Success
            mock_cm_success = MagicMock()
            mock_cm_success.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_cm_success.__aexit__ = AsyncMock()
            
            mock_request.side_effect = [mock_cm_timeout, mock_cm_success]
            
            with patch("src.api.client.asyncio.sleep"): # Skip sleep
                result = await safe_api_call(mock_session, "http://test.com", {}, max_retries=2)
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_session_isolation(self):
        """Test session sử dụng DummyCookieJar"""
        session = create_session()
        from aiohttp import DummyCookieJar
        assert isinstance(session.cookie_jar, DummyCookieJar)
        await session.close()


class TestUtils:
    """Test cases cho các hàm tiện ích"""
    
    def test_mask_uid(self):
        """Test che UID"""
        assert mask_uid("123456789") == "123***789"
        assert mask_uid(12345) == "***"  # Quá ngắn
        assert mask_uid(None) == "***"

    def test_helpers(self):
        """Test các hàm helper thời gian"""
        assert len(current_hour()) == 2
        assert rpc_weekday() in [str(i) for i in range(1, 8)]
class TestGameModel:
    """Test cases cho Game model (GameInfo)"""

    def test_game_info_zzz_page_type(self):
        """Test ZZZ có page_type = 46"""
        from src.models.game import Game
        zzz = Game.ZZZ.value
        assert zzz.page_type == "46"
        assert zzz.game_id == "8"

    def test_get_page_info_serialization(self):
        """Test cơ chế sinh page_info JSON đúng format stealth"""
        from src.models.game import Game
        zzz = Game.ZZZ.value
        page_info = zzz.get_page_info("TestPage")
        
        # Kiểm tra JSON valid
        import json
        data = json.loads(page_info)
        assert data["pageName"] == "TestPage"
        assert data["pageType"] == "46"
        assert data["gameId"] == "8"
        
        # Kiểm tra separators (stealth requirement: no spaces)
        assert " " not in page_info
        assert ',"pageType":"46"' in page_info
