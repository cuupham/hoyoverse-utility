"""Tests grouped by their implementation owner."""

from src.api.request_builder import (
    build_page_info,
    build_rpc_headers,
    build_sign_headers,
    build_sign_params,
    build_sign_payload,
    build_source_info,
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

    def test_genshin_sign_game(self, mock_account):
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
        payload = build_sign_payload(Game.GENSHIN)
        assert "act_id" in payload
        assert "lang" not in payload
        assert build_sign_params(Game.GENSHIN) == {"lang": "en-us"}

    def test_build_sign_payload_star_rail(self):
        payload = build_sign_payload(Game.STAR_RAIL)
        assert "act_id" in payload
        assert payload["lang"] == "en-us"
        assert build_sign_params(Game.STAR_RAIL) is None

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

    def test_build_page_info_account_wide(self):
        import json

        data = json.loads(build_page_info(page_name="HomePage"))
        assert data["pageType"] == ""
        assert data["gameId"] == ""
        assert data["pageArrangement"] == ""

    def test_build_source_info(self):
        import json

        data = json.loads(build_source_info("HomeUserPage", "Post", "42"))
        assert data["sourceName"] == "HomeUserPage"
        assert data["sourceId"] == "42"
        assert json.loads(build_source_info())["sourceName"] == ""

    def test_regions_completeness(self):
        """Mỗi game phải có 4 regions"""
        for game in Game:
            assert len(REGIONS[game]) == 4, f"{game.value.name} thiếu regions"
