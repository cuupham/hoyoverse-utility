"""Tests cho core components (Models, Utils, Client)"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from src.models.account import Account
from src.api.client import safe_api_call, create_session, reset_semaphore
from src.utils.security import mask_uid
from src.utils.helpers import current_hour, rpc_weekday
from tests.conftest import MockAsyncCM


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
        cookie = "ltoken_v2=v2; ltuid_v2=123"
        with pytest.raises(ValueError) as excinfo:
            Account.from_env("BAD_ACC", cookie)
        assert "Missing required cookies" in str(excinfo.value)

    def test_account_cookies_immutable(self):
        """Test cookies dict thực sự immutable (MappingProxyType)"""
        cookie = "ltoken_v2=v2; ltuid_v2=123; cookie_token_v2=c2; account_id_v2=456; _MHYUUID=m1; _HYVUUID=h1"
        acc = Account.from_env("ACC_1", cookie)
        with pytest.raises(TypeError):
            acc.cookies["new_key"] = "should_fail"


class TestApiClient:
    """Test cases cho safe_api_call và session isolation"""

    @pytest.fixture(autouse=True)
    def _reset_semaphore(self):
        """Reset semaphore trước mỗi test để tránh state leak"""
        reset_semaphore()
        yield
        reset_semaphore()

    @pytest.mark.asyncio
    async def test_safe_api_call_retry_on_timeout(self, mock_session):
        """Test cơ chế retry khi gặp timeout - lần 1 timeout, lần 2 thành công"""
        mock_resp_200 = MagicMock()
        mock_resp_200.status = 200
        mock_resp_200.json = AsyncMock(return_value={"retcode": 0})

        mock_session.request = MagicMock()
        mock_session.request.side_effect = [
            MockAsyncCM(side_effect=asyncio.TimeoutError()),
            MockAsyncCM(return_value=mock_resp_200),
        ]

        with patch("src.api.client.asyncio.sleep"):
            with patch("src.api.client._get_semaphore"):
                result = await safe_api_call(mock_session, "http://test.com", {}, max_retries=2)
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_safe_api_call_retry_on_5xx(self, mock_session):
        """Test retry cho HTTP 5xx server errors"""
        mock_resp_502 = MagicMock()
        mock_resp_502.status = 502

        mock_resp_200 = MagicMock()
        mock_resp_200.status = 200
        mock_resp_200.json = AsyncMock(return_value={"retcode": 0})

        mock_session.request = MagicMock()
        mock_session.request.side_effect = [
            MockAsyncCM(return_value=mock_resp_502),
            MockAsyncCM(return_value=mock_resp_200),
        ]

        with patch("src.api.client.asyncio.sleep"):
            with patch("src.api.client._get_semaphore"):
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
        assert mask_uid(12345) == "***"
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
        import json

        zzz = Game.ZZZ.value
        page_info = zzz.get_page_info("TestPage")

        data = json.loads(page_info)
        assert data["pageName"] == "TestPage"
        assert data["pageType"] == "46"
        assert data["gameId"] == "8"
        assert " " not in page_info
