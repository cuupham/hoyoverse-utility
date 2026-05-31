"""Tests cho fetch_all_uids (1-request, map ngược game_biz/region → model)"""

import pytest
from unittest.mock import patch

from src.models.game import Game
from src.api.redeem_fetch import fetch_all_uids


def _api_result(roles: list[dict]) -> dict:
    """Wrap roles list theo format safe_api_call: {success, data: {retcode, data: {list}}}."""
    return {"success": True, "data": {"retcode": 0, "data": {"list": roles}}}


class TestFetchAllUids:
    @pytest.mark.asyncio
    async def test_maps_real_response_to_games_and_regions(self, mock_session, mock_account):
        """Response thật (SR asia + ZZZ asia) map đúng về Game + region_code."""
        roles = [
            {"game_biz": "hkrpg_global", "region": "prod_official_asia", "game_uid": "841565230"},
            {"game_biz": "nap_global", "region": "prod_gf_jp", "game_uid": "1316327131"},
        ]
        with patch("src.api.redeem_fetch.safe_api_call", return_value=_api_result(roles)):
            result = await fetch_all_uids(mock_session, mock_account)

        assert result[Game.STAR_RAIL] == {"asia": "841565230"}
        assert result[Game.ZZZ] == {"asia": "1316327131"}
        assert result[Game.GENSHIN] == {}

    @pytest.mark.asyncio
    async def test_multiple_regions_same_game(self, mock_session, mock_account):
        """1 game nhiều region → capture tất cả."""
        roles = [
            {"game_biz": "hk4e_global", "region": "os_asia", "game_uid": "800000001"},
            {"game_biz": "hk4e_global", "region": "os_usa", "game_uid": "600000001"},
            {"game_biz": "hk4e_global", "region": "os_euro", "game_uid": "700000001"},
        ]
        with patch("src.api.redeem_fetch.safe_api_call", return_value=_api_result(roles)):
            result = await fetch_all_uids(mock_session, mock_account)

        assert result[Game.GENSHIN] == {
            "asia": "800000001",
            "usa": "600000001",
            "euro": "700000001",
        }

    @pytest.mark.asyncio
    async def test_makes_single_api_call(self, mock_session, mock_account):
        """Tối ưu cốt lõi: CHỈ 1 request (trước đây 12)."""
        with patch("src.api.redeem_fetch.safe_api_call", return_value=_api_result([])) as mock_call:
            await fetch_all_uids(mock_session, mock_account)

        assert mock_call.call_count == 1
        # Không gửi region/game_biz params (account-wide query)
        _, kwargs = mock_call.call_args
        assert kwargs.get("params") is None

    @pytest.mark.asyncio
    async def test_unsupported_game_biz_skipped(self, mock_session, mock_account):
        """game_biz lạ (Honkai 3rd, Tears of Themis) → bỏ qua, không crash."""
        roles = [
            {"game_biz": "bh3_global", "region": "overseas01", "game_uid": "100000001"},
            {"game_biz": "hkrpg_global", "region": "prod_official_asia", "game_uid": "841565230"},
        ]
        with patch("src.api.redeem_fetch.safe_api_call", return_value=_api_result(roles)):
            result = await fetch_all_uids(mock_session, mock_account)

        assert result[Game.STAR_RAIL] == {"asia": "841565230"}
        assert all(uids == {} for g, uids in result.items() if g is not Game.STAR_RAIL)

    @pytest.mark.asyncio
    async def test_unknown_region_skipped(self, mock_session, mock_account):
        """region không có trong REGIONS map → bỏ qua role đó."""
        roles = [
            {"game_biz": "hkrpg_global", "region": "prod_official_unknown", "game_uid": "999999999"},
        ]
        with patch("src.api.redeem_fetch.safe_api_call", return_value=_api_result(roles)):
            result = await fetch_all_uids(mock_session, mock_account)

        assert all(uids == {} for uids in result.values())

    @pytest.mark.asyncio
    async def test_role_missing_uid_skipped(self, mock_session, mock_account):
        """Role thiếu game_uid → bỏ qua."""
        roles = [
            {"game_biz": "hkrpg_global", "region": "prod_official_asia"},
        ]
        with patch("src.api.redeem_fetch.safe_api_call", return_value=_api_result(roles)):
            result = await fetch_all_uids(mock_session, mock_account)

        assert result[Game.STAR_RAIL] == {}

    @pytest.mark.asyncio
    async def test_empty_list_no_characters(self, mock_session, mock_account):
        """List rỗng (account chưa tạo nhân vật game nào) → tất cả rỗng."""
        with patch("src.api.redeem_fetch.safe_api_call", return_value=_api_result([])):
            result = await fetch_all_uids(mock_session, mock_account)

        assert all(uids == {} for uids in result.values())
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_api_failure_returns_empty(self, mock_session, mock_account):
        """API call thất bại → trả dict rỗng (không crash)."""
        with patch("src.api.redeem_fetch.safe_api_call", return_value={"success": False, "message": "timeout"}):
            result = await fetch_all_uids(mock_session, mock_account)

        assert all(uids == {} for uids in result.values())
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_retcode_not_zero_returns_empty(self, mock_session, mock_account):
        """API retcode != 0 (cookie hết hạn) → trả dict rỗng."""
        bad = {"success": True, "data": {"retcode": -100, "message": "Please login"}}
        with patch("src.api.redeem_fetch.safe_api_call", return_value=bad):
            result = await fetch_all_uids(mock_session, mock_account)

        assert all(uids == {} for uids in result.values())
