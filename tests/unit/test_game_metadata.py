"""Tests grouped by their implementation owner."""

from src.api.request_builder import build_page_info


class TestGameModel:
    """Test cases cho Game model (GameInfo)"""

    def test_game_info_zzz_page_type(self):
        """Test ZZZ có page_type = 46"""
        from src.models.game import Game

        zzz = Game.ZZZ.value
        assert zzz.page_type == "46"
        assert zzz.game_id == "8"

    def test_build_page_info_serialization(self):
        """Test cơ chế sinh page_info JSON đúng format stealth"""
        import json

        from src.models.game import Game

        zzz = Game.ZZZ.value
        page_info = build_page_info(zzz, "TestPage")

        data = json.loads(page_info)
        assert data["pageName"] == "TestPage"
        assert data["pageType"] == "46"
        assert data["gameId"] == "8"
        assert " " not in page_info
