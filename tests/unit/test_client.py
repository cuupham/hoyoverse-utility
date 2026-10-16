"""Tests grouped by their implementation owner."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from src.api.client import (
    _get_semaphore,
    _sanitize_error_message,
    create_session,
    request_json,
    reset_semaphore,
)
from tests.conftest import MockAsyncCM


class TestApiClient:
    """Test cases cho request_json và session isolation"""

    @pytest.fixture(autouse=True)
    def _reset_semaphore(self):
        """Reset semaphore trước mỗi test để tránh state leak"""
        reset_semaphore()
        yield
        reset_semaphore()

    @pytest.mark.asyncio
    async def test_request_json_retry_on_timeout(self, mock_session):
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
                result = await request_json(
                    mock_session, "http://test.com", {}, max_attempts=2
                )
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_request_json_retry_on_5xx(self, mock_session):
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
                result = await request_json(
                    mock_session, "http://test.com", {}, max_attempts=2
                )
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_session_isolation(self):
        """Test session sử dụng DummyCookieJar"""
        session = create_session()
        from aiohttp import DummyCookieJar

        assert isinstance(session.cookie_jar, DummyCookieJar)
        await session.close()


class TestErrorSanitization:
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


class TestRequestJsonFailures:
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

        mock_session.request = MagicMock(
            side_effect=[
                MockAsyncCM(return_value=mock_resp_429),
                MockAsyncCM(return_value=mock_resp_200),
            ]
        )

        with (
            patch("src.api.client.asyncio.sleep"),
            patch("src.api.client._get_semaphore"),
        ):
            result = await request_json(mock_session, "http://test.com", {})
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
            result = await request_json(
                mock_session, "http://test.com", {}, max_attempts=2
            )
            assert result["success"] is False
            assert result["error"] == "network"

    @pytest.mark.asyncio
    async def test_content_type_error_no_retry(self, mock_session):
        """ContentTypeError → immediate fail, no retry"""
        mock_session.request = MagicMock(
            side_effect=[
                MockAsyncCM(
                    side_effect=aiohttp.ContentTypeError(MagicMock(), MagicMock())
                )
            ]
        )
        with (
            patch("src.api.client.asyncio.sleep"),
            patch("src.api.client._get_semaphore"),
        ):
            result = await request_json(mock_session, "http://test.com", {})
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
            result = await request_json(mock_session, "http://test.com", {})
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
            result = await request_json(
                mock_session, "http://test.com", {}, max_attempts=3
            )
            assert result["success"] is False
            assert "502" in result["message"]

    @pytest.mark.asyncio
    async def test_post_with_json_data(self, mock_session):
        """POST method với json_data"""
        mock_resp = MagicMock(status=200)
        mock_resp.json = AsyncMock(return_value={"retcode": 0})
        mock_session.request = MagicMock(
            return_value=MockAsyncCM(return_value=mock_resp)
        )

        with (
            patch("src.api.client.asyncio.sleep"),
            patch("src.api.client._get_semaphore"),
        ):
            result = await request_json(
                mock_session,
                "http://test.com",
                {},
                json_data={"key": "val"},
                method="POST",
            )
            assert result["success"] is True
            # Verify json kwarg was passed
            call_kwargs = mock_session.request.call_args[1]
            assert call_kwargs["json"] == {"key": "val"}


class TestSemaphore:
    @pytest.fixture(autouse=True)
    def _reset(self):
        reset_semaphore()
        yield
        reset_semaphore()

    async def test_lazy_init(self):
        """_get_semaphore() lazy init tạo Semaphore khi chưa có"""
        import asyncio

        sem = _get_semaphore()
        assert isinstance(sem, asyncio.Semaphore)

    async def test_reuses_existing(self):
        """Gọi 2 lần trả về cùng instance"""
        sem1 = _get_semaphore()
        sem2 = _get_semaphore()
        assert sem1 is sem2

    @pytest.mark.asyncio
    async def test_request_json_with_params(self, mock_session):
        """Verify params kwarg gets passed through"""
        mock_resp = MagicMock(status=200)
        mock_resp.json = AsyncMock(return_value={"retcode": 0})
        mock_session.request = MagicMock(
            return_value=MockAsyncCM(return_value=mock_resp)
        )

        with (
            patch("src.api.client.asyncio.sleep"),
            patch("src.api.client._get_semaphore"),
        ):
            result = await request_json(
                mock_session, "http://test.com", {}, params={"key": "val"}
            )
            assert result["success"] is True
            call_kwargs = mock_session.request.call_args[1]
            assert call_kwargs["params"] == {"key": "val"}

    @pytest.mark.asyncio
    async def test_timeout_all_retries_exhausted(self, mock_session):
        """Tất cả retries timeout → max_attempts error"""
        mock_session.request = MagicMock(
            side_effect=[MockAsyncCM(side_effect=asyncio.TimeoutError())] * 2
        )
        with (
            patch("src.api.client.asyncio.sleep"),
            patch("src.api.client._get_semaphore"),
        ):
            result = await request_json(
                mock_session, "http://test.com", {}, max_attempts=2
            )
            assert result["success"] is False
            assert result["error"] == "timeout"


class TestRequestAttemptValidation:
    @pytest.mark.parametrize("max_attempts", [0, -1])
    async def test_nonpositive_attempt_count_rejected(self, mock_session, max_attempts):
        with pytest.raises(ValueError, match="max_attempts must be at least 1"):
            await request_json(
                mock_session, "https://example.test", {}, max_attempts=max_attempts
            )
        mock_session.request.assert_not_called()
