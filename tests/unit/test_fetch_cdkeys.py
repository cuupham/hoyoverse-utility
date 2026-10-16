"""Tests cho fetch CDKeys functionality"""

from unittest.mock import patch

import pytest

from src.api.redeem_fetch import fetch_all_cdkeys, fetch_cdkeys
from src.models.game import Game
from src.models.results import ProviderResult


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


class TestFetchAllCdkeys:
    """Test cases cho fetch_all_cdkeys function"""

    @pytest.mark.asyncio
    async def test_fetch_all_games_parallel(self, mock_session, mock_account):
        """Test fetch CDKeys cho tất cả games song song"""

        async def mock_fetch_cdkeys(session, account, game):
            if game == Game.GENSHIN:
                return ProviderResult(["GS1", "GS2"])
            elif game == Game.STAR_RAIL:
                return ProviderResult(["HSR1"])
            else:
                return ProviderResult([])

        with patch("src.api.redeem_fetch.fetch_cdkeys", side_effect=mock_fetch_cdkeys):
            result = await fetch_all_cdkeys(mock_session, mock_account)

            assert Game.GENSHIN in result
            assert Game.STAR_RAIL in result
            assert Game.ZZZ in result

            assert len(result[Game.GENSHIN].data) == 2
            assert len(result[Game.STAR_RAIL].data) == 1
            assert len(result[Game.ZZZ].data) == 0

    @pytest.mark.asyncio
    async def test_fetch_all_games_all_empty(self, mock_session, mock_account):
        """Test khi tất cả games đều không có codes"""
        with patch(
            "src.api.redeem_fetch.fetch_cdkeys", return_value=ProviderResult([])
        ):
            result = await fetch_all_cdkeys(mock_session, mock_account)

            assert all(len(codes.data) == 0 for codes in result.values())

    @pytest.mark.asyncio
    async def test_fetch_all_games_partial_failure(self, mock_session, mock_account):
        """Test khi một số games lỗi"""
        call_count = 0

        async def mock_fetch_with_error(session, account, game):
            nonlocal call_count
            call_count += 1
            if game == Game.STAR_RAIL:
                return ProviderResult([], error="network")
            return ProviderResult(["CODE1"])

        with patch(
            "src.api.redeem_fetch.fetch_cdkeys", side_effect=mock_fetch_with_error
        ):
            result = await fetch_all_cdkeys(mock_session, mock_account)

            assert len(result) == 3
            assert call_count == 3
            assert not result[Game.STAR_RAIL].success
            assert result[Game.GENSHIN].data == ["CODE1"]


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
