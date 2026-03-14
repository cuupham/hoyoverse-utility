"""Tests cho fetch_uid và fetch_all_uids"""

import pytest
from unittest.mock import patch

from src.models.game import Game, REGIONS
from src.api.redeem_fetch import fetch_uid, fetch_all_uids


class TestFetchUid:
    @pytest.mark.asyncio
    async def test_success(self, mock_session, mock_account):
        """Fetch UID thành công"""
        mock_response = {
            "success": True,
            "data": {"retcode": 0, "data": {"list": [{"game_uid": "800123456"}]}},
        }
        with patch("src.api.redeem_fetch.safe_api_call", return_value=mock_response):
            uid = await fetch_uid(mock_session, mock_account, Game.GENSHIN, "asia")

        assert uid == "800123456"

    @pytest.mark.asyncio
    async def test_invalid_region(self, mock_session, mock_account):
        """Region không tồn tại → None"""
        uid = await fetch_uid(mock_session, mock_account, Game.GENSHIN, "invalid_region")
        assert uid is None

    @pytest.mark.asyncio
    async def test_api_failure(self, mock_session, mock_account):
        """API call thất bại → None"""
        with patch("src.api.redeem_fetch.safe_api_call", return_value={"success": False, "message": "timeout"}):
            uid = await fetch_uid(mock_session, mock_account, Game.STAR_RAIL, "asia")

        assert uid is None

    @pytest.mark.asyncio
    async def test_retcode_not_zero(self, mock_session, mock_account):
        """API trả retcode != 0 → None"""
        mock_response = {"success": True, "data": {"retcode": -100, "message": "error"}}
        with patch("src.api.redeem_fetch.safe_api_call", return_value=mock_response):
            uid = await fetch_uid(mock_session, mock_account, Game.ZZZ, "asia")

        assert uid is None

    @pytest.mark.asyncio
    async def test_empty_uid_list(self, mock_session, mock_account):
        """UID list rỗng (chưa tạo nhân vật) → None"""
        mock_response = {"success": True, "data": {"retcode": 0, "data": {"list": []}}}
        with patch("src.api.redeem_fetch.safe_api_call", return_value=mock_response):
            uid = await fetch_uid(mock_session, mock_account, Game.GENSHIN, "usa")

        assert uid is None

    @pytest.mark.asyncio
    async def test_missing_game_uid_key(self, mock_session, mock_account):
        """list[0] không có key game_uid → None"""
        mock_response = {"success": True, "data": {"retcode": 0, "data": {"list": [{"other": "val"}]}}}
        with patch("src.api.redeem_fetch.safe_api_call", return_value=mock_response):
            uid = await fetch_uid(mock_session, mock_account, Game.GENSHIN, "asia")

        assert uid is None


class TestFetchAllUids:
    @pytest.mark.asyncio
    async def test_all_games_all_regions(self, mock_session, mock_account):
        """Fetch UIDs cho 3 games × 4 regions"""
        async def mock_fetch(session, account, game, region):
            if game == Game.GENSHIN and region == "asia":
                return "800001"
            if game == Game.STAR_RAIL and region == "euro":
                return "130001"
            return None

        with patch("src.api.redeem_fetch.fetch_uid", side_effect=mock_fetch):
            result = await fetch_all_uids(mock_session, mock_account)

        assert result[Game.GENSHIN] == {"asia": "800001"}
        assert result[Game.STAR_RAIL] == {"euro": "130001"}
        assert result[Game.ZZZ] == {}

    @pytest.mark.asyncio
    async def test_no_uids_found(self, mock_session, mock_account):
        """Không tìm thấy UID nào"""
        with patch("src.api.redeem_fetch.fetch_uid", return_value=None):
            result = await fetch_all_uids(mock_session, mock_account)

        assert all(uids == {} for uids in result.values())
        assert len(result) == 3  # vẫn có 3 games

    @pytest.mark.asyncio
    async def test_correct_number_of_calls(self, mock_session, mock_account):
        """Phải gọi fetch_uid đúng 3 games × 4 regions = 12 lần"""
        with patch("src.api.redeem_fetch.fetch_uid", return_value=None) as mock_fetch:
            await fetch_all_uids(mock_session, mock_account)

        total_regions = sum(len(regions) for regions in REGIONS.values())
        assert mock_fetch.call_count == total_regions
