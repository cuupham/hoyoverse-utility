"""Tests cho fetch CDKeys functionality"""

from unittest.mock import patch

import pytest

from src.api.redeem_fetch import fetch_cdkeys
from src.models.game import Game


class TestFetchCdkeys:
    """Test cases cho fetch_cdkeys function"""

    @pytest.mark.asyncio
    async def test_fetch_cdkeys_genshin_success(self, mock_session, mock_account):
        """Test fetch CDKeys cho Genshin thành công"""
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
                },
            },
        }

        with patch("src.api.redeem_fetch.request_json") as mock_api:
            mock_api.return_value = mock_api_response

            result = await fetch_cdkeys(mock_session, mock_account, Game.GENSHIN)

            assert result.success
            assert result.data == ["GENSHINGIFT2024", "PRIMOGEMS500"]

    @pytest.mark.asyncio
    async def test_fetch_cdkeys_empty_response(self, mock_session, mock_account):
        """Test fetch CDKeys khi API trả về rỗng"""
        mock_api_response = {
            "success": True,
            "data": {"retcode": 0, "data": {"modules": []}},
        }

        with patch("src.api.redeem_fetch.request_json") as mock_api:
            mock_api.return_value = mock_api_response

            result = await fetch_cdkeys(mock_session, mock_account, Game.STAR_RAIL)

            assert result.data == []
            assert result.success

    @pytest.mark.asyncio
    async def test_fetch_cdkeys_api_error(self, mock_session, mock_account):
        """Test fetch CDKeys khi API lỗi"""
        with patch("src.api.redeem_fetch.request_json") as mock_api:
            mock_api.return_value = {
                "success": False,
                "error": "network",
                "message": "Connection failed",
            }

            result = await fetch_cdkeys(mock_session, mock_account, Game.ZZZ)

            assert result.data == []
            assert result.error == "Connection failed"

    @pytest.mark.asyncio
    async def test_fetch_cdkeys_invalid_structure(self, mock_session, mock_account):
        """Test fetch CDKeys khi response structure không đúng"""
        mock_api_response = {
            "success": True,
            "data": {"retcode": 0, "data": {"unexpected_field": "value"}},
        }

        with patch("src.api.redeem_fetch.request_json") as mock_api:
            mock_api.return_value = mock_api_response

            result = await fetch_cdkeys(mock_session, mock_account, Game.GENSHIN)

            assert result.data == []
            assert not result.success


class TestFetchCdkeysRetcode:
    @pytest.mark.asyncio
    async def test_retcode_not_zero(self, mock_session, mock_account):
        """fetch_cdkeys khi retcode != 0 → return []"""
        mock_resp = {"success": True, "data": {"retcode": -1, "message": "error"}}
        with patch("src.api.redeem_fetch.request_json", return_value=mock_resp):
            result = await fetch_cdkeys(mock_session, mock_account, Game.GENSHIN)
        assert result.data == []
        assert result.error == "error"
        assert result.retcode == -1
