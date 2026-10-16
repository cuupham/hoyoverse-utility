"""Tests cho display.py - table format check-in/redeem"""

from unittest.mock import patch

from src.config import SYSTEM_MESSAGES
from src.models.game import Game
from src.utils.display import (
    _plural,
    _short_checkin_status,
    _short_redeem_status,
    display_cdkeys,
    display_checkin,
    display_redeem,
    display_redeem_results,
    display_uids,
)


class TestPlural:
    def test_singular(self):
        assert _plural(1, "code") == "1 code"

    def test_plural(self):
        assert _plural(3, "code") == "3 codes"

    def test_zero(self):
        assert _plural(0, "region") == "0 regions"


class TestShortCheckinStatus:
    def test_already_signed(self):
        result = {
            "success": True,
            "status": "already_claimed",
            "message": SYSTEM_MESSAGES["CHECKIN_ALREADY"],
            "day": 14,
        }
        assert _short_checkin_status(result) == "✓ Đã điểm danh"

    def test_new_sign(self):
        result = {
            "success": True,
            "status": "claimed",
            "message": SYSTEM_MESSAGES["CHECKIN_SUCCESS"],
            "day": 15,
        }
        assert _short_checkin_status(result) == "✓ Ngày 15"

    def test_no_character_status_is_independent_of_provider_message(self):
        result = {
            "success": False,
            "status": "no_character",
            "message": "Translated provider text",
        }
        assert "Chưa tạo nhân vật" in _short_checkin_status(result)

    def test_error_containing_character_is_not_reclassified(self):
        result = {
            "success": False,
            "status": "failed",
            "message": "Character service unavailable",
        }
        assert _short_checkin_status(result).startswith("✗")

    def test_already_claimed_status_is_independent_of_translation(self):
        result = {
            "success": True,
            "status": "already_claimed",
            "message": "Other language",
            "day": 14,
        }
        assert _short_checkin_status(result) == SYSTEM_MESSAGES["CHECKIN_ALREADY_SHORT"]

    def test_other_error_truncated(self):
        result = {"success": False, "message": "A" * 50}
        status = _short_checkin_status(result)
        assert status.startswith("✗")
        assert len(status) <= 25


class TestShortRedeemStatus:
    def test_success(self):
        assert "Thành công" in _short_redeem_status({"success": True, "message": "OK"})

    def test_failed(self):
        status = _short_redeem_status({"success": False, "message": "Đã sử dụng"})
        assert "✗" in status
        assert "Đã sử dụng" in status


class TestDisplayCheckin:
    def test_empty_results(self):
        """Không crash khi all_results rỗng"""
        with patch("src.utils.display.log_print") as mock_log:
            display_checkin({})
            # Chỉ in header + blank line
            assert mock_log.call_count >= 1

    def test_table_format(self):
        """Verify table output có header + rows"""
        results = {
            "ACC_1": {
                Game.GENSHIN: {
                    "success": True,
                    "status": "already_claimed",
                    "message": SYSTEM_MESSAGES["CHECKIN_ALREADY"],
                    "day": 14,
                },
                Game.STAR_RAIL: {
                    "success": True,
                    "status": "claimed",
                    "message": SYSTEM_MESSAGES["CHECKIN_SUCCESS"],
                    "day": 5,
                },
                Game.ZZZ: {
                    "success": False,
                    "status": "no_character",
                    "message": "No character detected",
                },
            },
        }
        lines = []
        with patch(
            "src.utils.display.log_print", side_effect=lambda m="": lines.append(m)
        ):
            display_checkin(results)

        assert any("Account" in line for line in lines)  # header
        assert any("ACC_1" in line for line in lines)  # data row
        assert any("Đã điểm danh" in line for line in lines)
        assert any("Ngày 5" in line for line in lines)

    def test_multi_account_rows(self):
        """Mỗi account = 1 dòng"""
        results = {
            f"ACC_{i}": {
                game: {
                    "success": True,
                    "status": "already_claimed",
                    "message": SYSTEM_MESSAGES["CHECKIN_ALREADY"],
                    "day": 1,
                }
                for game in Game
            }
            for i in range(1, 4)
        }
        lines = []
        with patch(
            "src.utils.display.log_print", side_effect=lambda m="": lines.append(m)
        ):
            display_checkin(results)

        data_lines = [l for l in lines if l.startswith("ACC_")]
        assert len(data_lines) == 3


class TestDisplayCdkeys:
    def test_with_codes(self):
        lines = []
        cdkeys = {
            Game.GENSHIN: ["CODE1", "CODE2"],
            Game.STAR_RAIL: [],
            Game.ZZZ: ["ZZZ1"],
        }
        with patch(
            "src.utils.display.log_print", side_effect=lambda m="": lines.append(m)
        ):
            display_cdkeys(cdkeys)

        output = "\n".join(lines)
        assert "CODE1, CODE2" in output  # comma separated, not Python list
        assert "2 codes" in output
        assert "1 code" in output  # singular
        assert SYSTEM_MESSAGES["SYSTEM_NO_CODES"] in output

    def test_all_empty(self):
        lines = []
        cdkeys = {game: [] for game in Game}
        with patch(
            "src.utils.display.log_print", side_effect=lambda m="": lines.append(m)
        ):
            display_cdkeys(cdkeys)

        assert all(SYSTEM_MESSAGES["SYSTEM_NO_CODES"] in l for l in lines if l)


class TestDisplayUids:
    def test_with_uids(self):
        lines = []
        uids = {
            "ACC_1": {
                Game.GENSHIN: {"asia": "123"},
                Game.STAR_RAIL: {},
                Game.ZZZ: {"asia": "456"},
            }
        }
        with patch(
            "src.utils.display.log_print", side_effect=lambda m="": lines.append(m)
        ):
            display_uids(uids)

        output = "\n".join(lines)
        assert "ACC_1" in output
        assert "Genshin Impact(asia)" in output
        assert "Zenless Zone Zero(asia)" in output

    def test_no_uids(self):
        lines = []
        uids = {"ACC_1": {game: {} for game in Game}}
        with patch(
            "src.utils.display.log_print", side_effect=lambda m="": lines.append(m)
        ):
            display_uids(uids)

        assert any(SYSTEM_MESSAGES["SYSTEM_NO_UIDS"] in l for l in lines)


class TestDisplayRedeemResults:
    def test_table_grouped_by_game(self):
        """Verify table nhóm theo game, codes làm cột"""
        results_map = {
            "ACC_1": {
                Game.STAR_RAIL: {
                    "asia": {
                        "CODE1": {"success": True, "message": "Thành công"},
                        "CODE2": {"success": False, "message": "Đã sử dụng"},
                    }
                }
            }
        }
        lines = []
        with patch(
            "src.utils.display.log_print", side_effect=lambda m="": lines.append(m)
        ):
            display_redeem_results(results_map)

        output = "\n".join(lines)
        assert "[Honkai: Star Rail]" in output
        assert "CODE1" in output
        assert "CODE2" in output
        assert "ACC_1" in output

    def test_account_name_hidden_when_same(self):
        """Account name ẩn khi trùng row trước"""
        results_map = {
            "ACC_2": {
                Game.STAR_RAIL: {
                    "asia": {"CODE1": {"success": True, "message": "OK"}},
                    "euro": {"CODE1": {"success": True, "message": "OK"}},
                }
            }
        }
        lines = []
        with patch(
            "src.utils.display.log_print", side_effect=lambda m="": lines.append(m)
        ):
            display_redeem_results(results_map)

        data_lines = [l for l in lines if "asia" in l or "euro" in l]
        assert "ACC_2" in data_lines[0]  # first row has name
        assert not data_lines[1].strip().startswith("ACC_2")  # second row hides name

    def test_empty_results(self):
        lines = []
        with patch(
            "src.utils.display.log_print", side_effect=lambda m="": lines.append(m)
        ):
            display_redeem_results({})
        assert len(lines) == 0

    def test_provider_rejection_keeps_retcode(self):
        results_map = {
            "ACC_1": {
                Game.ZZZ: {
                    "asia": {
                        "CODE1": {
                            "success": False,
                            "message": "Rejected",
                            "retcode": -2017,
                        }
                    }
                }
            }
        }
        lines = []
        with patch(
            "src.utils.display.log_print", side_effect=lambda m="": lines.append(m)
        ):
            display_redeem_results(results_map)

        assert any("-2017" in line for line in lines)


class TestDisplayRedeem:
    def test_no_codes_early_return(self):
        """Khi không có codes → chỉ hiện CDKeys, không hiện UIDs"""
        cdkeys = {game: [] for game in Game}
        uids = {"ACC_1": {game: {} for game in Game}}
        lines = []
        with (
            patch(
                "src.utils.display.log_print", side_effect=lambda m="": lines.append(m)
            ),
            patch("src.utils.display.log_info"),
        ):
            display_redeem(cdkeys, uids)

        output = "\n".join(lines)
        assert "CDKeys" in output
        assert "UIDs" not in output  # early return

    def test_with_codes_shows_uids(self):
        cdkeys = {Game.GENSHIN: ["CODE1"], Game.STAR_RAIL: [], Game.ZZZ: []}
        uids = {
            "ACC_1": {Game.GENSHIN: {"asia": "123"}, Game.STAR_RAIL: {}, Game.ZZZ: {}}
        }
        lines = []
        with patch(
            "src.utils.display.log_print", side_effect=lambda m="": lines.append(m)
        ):
            display_redeem(cdkeys, uids)

        output = "\n".join(lines)
        assert "CDKeys" in output
        assert "UIDs" in output


class TestDisplayTruncation:
    def test_long_status_truncated_in_table(self):
        """Status dài hơn column width bị cắt"""
        from src.utils.display import _short_redeem_status

        long_msg = {"success": False, "message": "A" * 100}
        status = _short_redeem_status(long_msg)
        # Status chứa đủ message ban đầu, truncation xảy ra trong display_redeem_results
        assert status.startswith("✗")

    def test_redeem_table_truncates_long_status(self):
        """display_redeem_results truncate status quá dài"""
        from src.utils.display import display_redeem_results

        results_map = {
            "ACC_1": {
                Game.ZZZ: {
                    "asia": {"CODE1": {"success": False, "message": "A" * 50}},
                }
            }
        }
        lines = []
        with patch(
            "src.utils.display.log_print", side_effect=lambda m="": lines.append(m)
        ):
            display_redeem_results(results_map)

        # Tìm dòng data chứa ".." (truncated)
        data_lines = [l for l in lines if "CODE1" in l or ".." in l]
        # Status phải bị truncate vì quá dài
        assert any(".." in l for l in data_lines)
