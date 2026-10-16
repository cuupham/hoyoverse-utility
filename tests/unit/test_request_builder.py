"""Tests grouped by their implementation owner."""

from src.api.request_builder import (
    build_page_info,
    build_rpc_headers,
    build_sign_headers,
    build_sign_payload,
)
from src.models.game import REGIONS, Game
from src.utils.timekeeping import unix_ms


class TestBuildRpcHeaders:
    def test_basic_headers(self, mock_account):
        headers = build_rpc_headers(
            mock_account, "hoyolab", '{"page":"test"}', "TestPage"
        )
        assert headers["Cookie"] == mock_account.cookie_str
        assert headers["x-rpc-device_id"] == mock_account.mhy_uuid
        assert headers["x-rpc-page_name"] == "TestPage"
        assert "x-rpc-signgame" not in headers

    def test_with_game_sign_game(self, mock_account):
        headers = build_rpc_headers(
            mock_account, "hoyolab", "{}", "Page", game=Game.STAR_RAIL
        )
        assert headers["x-rpc-signgame"] == "hkrpg"

    def test_without_game_no_sign_game(self, mock_account):
        headers = build_rpc_headers(
            mock_account, "hoyolab", "{}", "Page", game=Game.GENSHIN
        )
        assert headers["x-rpc-signgame"] == "hk4e"

    def test_unix_ms(self):
        ts = unix_ms()
        assert isinstance(ts, int)
        assert ts > 1_000_000_000_000


class TestSignRequestBuilder:
    def test_build_sign_payload_genshin(self):
        gs = Game.GENSHIN.value
        payload = build_sign_payload(gs)
        assert "act_id" in payload
        assert "lang" not in payload  # Genshin doesn't include lang

    def test_build_sign_payload_star_rail(self):
        sr = Game.STAR_RAIL.value
        payload = build_sign_payload(sr)
        assert "act_id" in payload
        assert payload["lang"] == "en-us"

    def test_build_sign_headers_genshin_specific(self, mock_account):
        headers = build_sign_headers(mock_account, Game.GENSHIN, "TestPage")
        assert headers["content-type"] == "application/json;charset=UTF-8"
        assert headers["x-rpc-app_version"] == ""
        assert headers["x-rpc-device_name"] == ""

    def test_build_sign_headers_star_rail_no_extras(self, mock_account):
        headers = build_sign_headers(mock_account, Game.STAR_RAIL, "TestPage")
        assert "content-type" not in headers
        assert "x-rpc-device_name" not in headers

    def test_build_page_info_non_home_game(self):
        gs = Game.GENSHIN.value
        import json

        data = json.loads(build_page_info(gs, "OtherPage"))
        assert data["pageArrangement"] == ""  # not "Hot"

    def test_regions_completeness(self):
        """Mỗi game phải có 4 regions"""
        for game in Game:
            assert len(REGIONS[game]) == 4, f"{game.value.name} thiếu regions"
