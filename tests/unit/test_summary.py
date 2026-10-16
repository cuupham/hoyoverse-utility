"""Tests cho summary.py - GitHub job summary"""

from src.config import VERDICT_FAILED
from src.models.game import Game
from src.utils.summary import SUMMARY_PATH_ENV, build_summary, write_job_summary


def _result(status, **extra):
    success = status in {"claimed", "already_claimed"}
    return {"success": success, "status": status, "message": "msg", **extra}


RESULTS = {
    "ACC_1": {
        Game.GENSHIN: _result("claimed", day=4),
        Game.STAR_RAIL: _result("no_character"),
        Game.ZZZ: _result("failed"),
    }
}


class TestBuildSummary:
    def test_table_has_one_row_per_account_and_column_per_game(self):
        lines = build_summary(RESULTS, [], 1.0).splitlines()
        header = next(line for line in lines if line.startswith("| Account"))
        row = next(line for line in lines if line.startswith("| ACC_1"))
        for game in Game:
            assert game.value.name in header
        assert header.count("|") == row.count("|")
        assert "✅ Ngày 4" in row and "➖" in row and "❌" in row

    def test_failures_are_listed(self):
        summary = build_summary(RESULTS, ["ACC_1 · boom"], 1.0)
        assert "- ACC_1 · boom" in summary
        assert VERDICT_FAILED in summary.splitlines()[0]

    def test_no_failure_section_when_clean(self):
        assert "\n- " not in build_summary(RESULTS, [], 1.0)

    def test_no_table_without_results(self):
        assert "| Account" not in build_summary({}, [], 1.0)


class TestWriteJobSummary:
    def test_appends_to_summary_file(self, tmp_path, monkeypatch):
        path = tmp_path / "summary.md"
        path.write_text("previous\n", encoding="utf-8")
        monkeypatch.setenv(SUMMARY_PATH_ENV, str(path))

        write_job_summary(RESULTS, [], 1.0)

        text = path.read_text(encoding="utf-8")
        assert text.startswith("previous\n")
        assert "ACC_1" in text

    def test_noop_without_env(self, monkeypatch, tmp_path):
        monkeypatch.delenv(SUMMARY_PATH_ENV, raising=False)
        monkeypatch.chdir(tmp_path)

        write_job_summary(RESULTS, [], 1.0)

        assert list(tmp_path.iterdir()) == []

    def test_unwritable_path_does_not_raise(self, tmp_path, monkeypatch):
        monkeypatch.setenv(SUMMARY_PATH_ENV, str(tmp_path / "missing" / "summary.md"))

        write_job_summary(RESULTS, [], 1.0)
