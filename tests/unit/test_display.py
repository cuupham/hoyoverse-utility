"""Tests cho display.py - table format check-in/redeem"""

from typing import get_args
from unittest.mock import patch

from src.config import (
    CHECKIN_LABELS,
    STATUS_ERROR,
    SYSTEM_MESSAGES,
    VERDICT_FAILED,
    VERDICT_OK,
)
from src.models.game import Game
from src.models.results import CheckinStatus
from src.utils.display import (
    _plural,
    _short_redeem_status,
    checkin_label,
    display_cdkeys,
    display_checkin,
    display_redeem,
    display_redeem_results,
    display_result,
    display_uids,
    format_result_line,
)


class TestPlural:
    def test_singular(self):
        assert _plural(1, "code") == "1 code"

    def test_plural(self):
        assert _plural(3, "code") == "3 codes"

    def test_zero(self):
        assert _plural(0, "region") == "0 regions"


def _result(status, **extra):
    success = status in {"claimed", "already_claimed"}
    return {"success": success, "status": status, "message": "msg", **extra}


class TestCheckinLabel:
    def test_every_status_has_a_label(self):
        assert set(CHECKIN_LABELS) == set(get_args(CheckinStatus))

    def test_already_claimed(self):
        assert checkin_label(_result("already_claimed", day=14)) == "Đã điểm danh"

    def test_claimed_shows_day(self):
        assert checkin_label(_result("claimed", day=15)) == "Ngày 15"

    def test_no_character_is_independent_of_provider_message(self):
        result = _result("no_character", message="Translated provider text")
        assert checkin_label(result) == "Chưa tạo nhân vật"

    def test_failed_message_is_not_reclassified(self):
        result = _result("failed", message="Character service unavailable")
        assert checkin_label(result) == STATUS_ERROR

    def test_challenge_asks_for_verification(self):
        assert checkin_label(_result("challenge")) == "Cần xác minh"

    def test_markdown_labels_prefix_the_icon(self):
        assert checkin_label(_result("claimed", day=3), markdown=True) == "✅ Ngày 3"
        assert checkin_label(_result("failed"), markdown=True) == f"❌ {STATUS_ERROR}"

    def test_labels_are_self_explanatory(self):
        """Không dùng mã viết tắt: người đọc log không cần bảng chú thích."""
        for text, _ in CHECKIN_LABELS.values():
            assert text == STATUS_ERROR or len(text) > 5


class TestShortRedeemStatus:
    def test_success(self):
        assert (
            _short_redeem_status({"success": True, "message": "OK"})
            == SYSTEM_MESSAGES["REDEEM_SUCCESS"]
        )

    def test_failed(self):
        status = _short_redeem_status({"success": False, "message": "Đã sử dụng"})
        assert status.startswith(STATUS_ERROR)
        assert "Đã sử dụng" in status


def _capture():
    lines = []
    return lines, patch(
        "src.utils.display.log_print", side_effect=lambda m="": lines.append(m)
    )


class TestDisplayCheckin:
    def test_empty_results(self):
        """Không crash khi all_results rỗng"""
        with patch("src.utils.display.log_print") as mock_log:
            display_checkin({})
            # Chỉ in header + blank line
            assert mock_log.call_count >= 1

    def test_table_format(self):
        """Verify table output có header + rows + legend"""
        results = {
            "ACC_1": {
                Game.GENSHIN: _result("already_claimed", day=14),
                Game.STAR_RAIL: _result("claimed", day=5),
                Game.ZZZ: _result("no_character"),
            },
        }
        lines, capture = _capture()
        with capture:
            display_checkin(results)

        header = next(line for line in lines if "Account" in line)
        row = next(line for line in lines if "ACC_1" in line)
        for game in Game:
            assert game.value.short_name in header
        assert row.split(maxsplit=1)[0] == "ACC_1"
        for cell in ("Đã điểm danh", "Ngày 5", "Chưa tạo nhân vật"):
            assert cell in row
        assert not any("vừa điểm danh" in line for line in lines)

    def test_columns_align_with_header(self):
        results = {
            "ACC_LONG_NAME": {game: _result("claimed", day=10) for game in Game},
            "A": {game: _result("failed") for game in Game},
        }
        lines, capture = _capture()
        with capture:
            display_checkin(results)

        header = next(line for line in lines if "Account" in line)
        rows = [line for line in lines if line.strip().startswith(("ACC_LONG", "A "))]
        assert len(rows) == 2
        for row in rows:
            for game in Game:
                col = header.index(game.value.short_name)
                assert row[col] != " "
                assert row[col - 1] == " "

    def test_rows_have_no_trailing_spaces(self):
        results = {"ACC_1": {game: _result("already_claimed") for game in Game}}
        lines, capture = _capture()
        with capture:
            display_checkin(results)

        assert all(line == line.rstrip() for line in lines)

    def test_multi_account_rows(self):
        """Mỗi account = 1 dòng"""
        results = {
            f"ACC_{i}": {game: _result("already_claimed", day=1) for game in Game}
            for i in range(1, 4)
        }
        lines, capture = _capture()
        with capture:
            display_checkin(results)

        data_lines = [line for line in lines if line.strip().startswith("ACC_")]
        assert len(data_lines) == 3


class TestResult:
    RESULTS = {
        "ACC_1": {
            Game.GENSHIN: _result("claimed", day=1),
            Game.STAR_RAIL: _result("already_claimed"),
            Game.ZZZ: _result("no_character"),
        },
        "ACC_2": {
            Game.GENSHIN: _result("failed"),
            Game.STAR_RAIL: _result("challenge"),
            Game.ZZZ: _result("already_claimed"),
        },
    }

    def test_counts_and_ok_verdict(self):
        line = format_result_line(self.RESULTS, [], 3.14)
        assert line.startswith(f"KẾT QUẢ  {VERDICT_OK}")
        assert "3 điểm danh" in line
        assert "1 chưa tạo nhân vật" in line
        assert "0 lỗi" in line
        assert line.endswith("3.1s")

    def test_failed_verdict(self):
        line = format_result_line(self.RESULTS, ["ACC_2 · x", "ACC_2 · y"], 1)
        assert VERDICT_FAILED in line
        assert "2 lỗi" in line

    def test_empty_results(self):
        assert "0 điểm danh" in format_result_line({}, [], 0)

    def test_failures_are_logged_as_errors_before_the_result_line(self):
        calls = []
        with (
            patch(
                "src.utils.display.log_error", side_effect=lambda *a: calls.append(a)
            ),
            patch(
                "src.utils.display.log_print", side_effect=lambda m="": calls.append(m)
            ),
        ):
            display_result(self.RESULTS, ["ACC_2 · boom"], 1)

        assert calls[0] == (SYSTEM_MESSAGES["FAILURE_SCOPE"], "ACC_2 · boom")
        assert VERDICT_FAILED in calls[1]


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
    def test_no_codes_prints_single_line(self):
        cdkeys = {game: [] for game in Game}
        uids = {"ACC_1": {game: {} for game in Game}}
        lines, capture = _capture()
        with capture:
            display_redeem(cdkeys, uids)

        assert lines[0] == SYSTEM_MESSAGES["REDEEM_NONE"]
        assert not any("UIDs" in line for line in lines)

    def test_fetch_errors_are_not_reported_as_no_codes(self):
        cdkeys = {game: [] for game in Game}
        lines, capture = _capture()
        with capture:
            display_redeem(cdkeys, {}, ["CDKeys / Genshin Impact: boom"])

        assert lines[0] == SYSTEM_MESSAGES["REDEEM_FETCH_FAILED"]

    def test_with_codes_shows_uids(self):
        cdkeys = {Game.GENSHIN: ["CODE1"], Game.STAR_RAIL: [], Game.ZZZ: []}
        uids = {
            "ACC_1": {Game.GENSHIN: {"asia": "123"}, Game.STAR_RAIL: {}, Game.ZZZ: {}}
        }
        lines, capture = _capture()
        with capture:
            display_redeem(cdkeys, uids)

        output = "\n".join(lines)
        assert SYSTEM_MESSAGES["SECTION_REDEEM"] in output
        assert "CODE1" in output
        assert "UIDs" in output


class TestDisplayTruncation:
    def test_long_status_truncated_in_table(self):
        """Status dài hơn column width bị cắt"""
        from src.utils.display import _short_redeem_status

        long_msg = {"success": False, "message": "A" * 100}
        status = _short_redeem_status(long_msg)
        # Status chứa đủ message ban đầu, truncation xảy ra trong display_redeem_results
        assert status.startswith(STATUS_ERROR)

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
