"""Tests cho fetch_all_uids (1-request, map ngược game_biz/region → model)"""

from unittest.mock import patch

import pytest

from src.api.redeem_fetch import fetch_all_uids
from src.models.game import Game


def _api_result(roles: list[dict]) -> dict:
    """Wrap roles list theo format request_json: {success, data: {retcode, data: {list}}}."""
    return {"success": True, "data": {"retcode": 0, "data": {"list": roles}}}


class TestFetchAllUids:
    @pytest.mark.asyncio
    async def test_maps_real_response_to_games_and_regions(
        self, mock_session, mock_account
    ):
        """Response thật (SR asia + ZZZ asia) map đúng về Game + region_code."""
        roles = [
            {
                "game_biz": "hkrpg_global",
                "region": "prod_official_asia",
                "game_uid": "841565230",
            },
            {
                "game_biz": "nap_global",
                "region": "prod_gf_jp",
                "game_uid": "1316327131",
            },
        ]
        with patch(
            "src.api.redeem_fetch.request_json", return_value=_api_result(roles)
        ):
            result = await fetch_all_uids(mock_session, mock_account)

        assert result.data[Game.STAR_RAIL] == {"asia": "841565230"}
        assert result.data[Game.ZZZ] == {"asia": "1316327131"}
        assert result.data[Game.GENSHIN] == {}

    @pytest.mark.asyncio
    async def test_multiple_regions_same_game(self, mock_session, mock_account):
        """1 game nhiều region → capture tất cả."""
        roles = [
            {"game_biz": "hk4e_global", "region": "os_asia", "game_uid": "800000001"},
            {"game_biz": "hk4e_global", "region": "os_usa", "game_uid": "600000001"},
            {"game_biz": "hk4e_global", "region": "os_euro", "game_uid": "700000001"},
        ]
        with patch(
            "src.api.redeem_fetch.request_json", return_value=_api_result(roles)
        ):
            result = await fetch_all_uids(mock_session, mock_account)

        assert result.data[Game.GENSHIN] == {
            "asia": "800000001",
            "usa": "600000001",
            "euro": "700000001",
        }

    @pytest.mark.asyncio
    async def test_makes_single_api_call(self, mock_session, mock_account):
        """Tối ưu cốt lõi: CHỈ 1 request (trước đây 12)."""
        with patch(
            "src.api.redeem_fetch.request_json", return_value=_api_result([])
        ) as mock_call:
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
            {
                "game_biz": "hkrpg_global",
                "region": "prod_official_asia",
                "game_uid": "841565230",
            },
        ]
        with patch(
            "src.api.redeem_fetch.request_json", return_value=_api_result(roles)
        ):
            result = await fetch_all_uids(mock_session, mock_account)

        assert result.data[Game.STAR_RAIL] == {"asia": "841565230"}
        assert all(
            uids == {} for g, uids in result.data.items() if g is not Game.STAR_RAIL
        )

    @pytest.mark.asyncio
    async def test_unknown_region_skipped(self, mock_session, mock_account):
        """region không có trong REGIONS map → bỏ qua role đó."""
        roles = [
            {
                "game_biz": "hkrpg_global",
                "region": "prod_official_unknown",
                "game_uid": "999999999",
            },
        ]
        with patch(
            "src.api.redeem_fetch.request_json", return_value=_api_result(roles)
        ):
            result = await fetch_all_uids(mock_session, mock_account)

        assert all(uids == {} for uids in result.data.values())

    @pytest.mark.asyncio
    async def test_missing_role_uid_returns_schema_error(
        self, mock_session, mock_account
    ):
        """Role thiếu game_uid → bỏ qua."""
        roles = [
            {"game_biz": "hkrpg_global", "region": "prod_official_asia"},
        ]
        with patch(
            "src.api.redeem_fetch.request_json", return_value=_api_result(roles)
        ):
            result = await fetch_all_uids(mock_session, mock_account)

        assert result.data[Game.STAR_RAIL] == {}
        assert not result.success

    @pytest.mark.asyncio
    async def test_empty_list_no_characters(self, mock_session, mock_account):
        """List rỗng (account chưa tạo nhân vật game nào) → tất cả rỗng."""
        with patch("src.api.redeem_fetch.request_json", return_value=_api_result([])):
            result = await fetch_all_uids(mock_session, mock_account)

        assert all(uids == {} for uids in result.data.values())
        assert len(result.data) == 3

    @pytest.mark.asyncio
    async def test_api_failure_returns_typed_error(self, mock_session, mock_account):
        """Transport failure remains an error even though its data mapping is empty."""
        with patch(
            "src.api.redeem_fetch.request_json",
            return_value={"success": False, "message": "timeout"},
        ):
            result = await fetch_all_uids(mock_session, mock_account)

        assert all(uids == {} for uids in result.data.values())
        assert len(result.data) == 3
        assert result.error == "timeout"

    @pytest.mark.asyncio
    async def test_nonzero_retcode_preserves_provider_error(
        self, mock_session, mock_account
    ):
        """Nonzero retcode preserves the provider error and numeric code."""
        bad = {"success": True, "data": {"retcode": -100, "message": "Please login"}}
        with patch("src.api.redeem_fetch.request_json", return_value=bad):
            result = await fetch_all_uids(mock_session, mock_account)

        assert all(uids == {} for uids in result.data.values())

        assert result.error == "Please login"
        assert result.retcode == -100
