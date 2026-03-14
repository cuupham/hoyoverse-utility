"""Tests cho headers.py - Dynamic User-Agent generation"""

from unittest.mock import patch, MagicMock

from src.constants import DEFAULT_CHROME_VERSION


class TestGetDynamicHeaders:
    def test_returns_required_keys(self):
        """Headers phải có user-agent, sec-ch-ua, sec-ch-ua-mobile, sec-ch-ua-platform"""
        from src.utils.headers import get_dynamic_headers

        headers = get_dynamic_headers()
        assert "user-agent" in headers
        assert "sec-ch-ua" in headers
        assert "sec-ch-ua-mobile" in headers
        assert "sec-ch-ua-platform" in headers

    def test_sec_ch_ua_contains_version(self):
        """sec-ch-ua phải chứa Chrome version number"""
        from src.utils.headers import get_dynamic_headers

        headers = get_dynamic_headers()
        assert "Chromium" in headers["sec-ch-ua"]
        assert "Google Chrome" in headers["sec-ch-ua"]

    def test_fallback_when_no_chrome_version_match(self):
        """Khi User-Agent không chứa Chrome/xx → fallback DEFAULT_CHROME_VERSION"""
        from src.utils.headers import get_dynamic_headers

        mock_ua = MagicMock()
        mock_ua.chrome = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

        with patch("src.utils.headers.UserAgent", return_value=mock_ua):
            headers = get_dynamic_headers()

        assert f'v="{DEFAULT_CHROME_VERSION}"' in headers["sec-ch-ua"]

    def test_extracts_chrome_version_correctly(self):
        """Parse đúng version từ Chrome/142 trong User-Agent"""
        from src.utils.headers import get_dynamic_headers

        mock_ua = MagicMock()
        mock_ua.chrome = "Mozilla/5.0 Chrome/142.0.6367.91 Safari/537.36"

        with patch("src.utils.headers.UserAgent", return_value=mock_ua):
            headers = get_dynamic_headers()

        assert 'v="142"' in headers["sec-ch-ua"]

    def test_platform_is_windows(self):
        """sec-ch-ua-platform phải là Windows"""
        from src.utils.headers import get_dynamic_headers

        headers = get_dynamic_headers()
        assert headers["sec-ch-ua-platform"] == '"Windows"'

    def test_mobile_is_false(self):
        """sec-ch-ua-mobile phải là ?0 (desktop)"""
        from src.utils.headers import get_dynamic_headers

        headers = get_dynamic_headers()
        assert headers["sec-ch-ua-mobile"] == "?0"


class TestDynamicHeadersCache:
    def test_module_level_cache_exists(self):
        """DYNAMIC_HEADERS phải được cache ở module level"""
        from src.utils.headers import DYNAMIC_HEADERS

        assert isinstance(DYNAMIC_HEADERS, dict)
        assert "user-agent" in DYNAMIC_HEADERS
