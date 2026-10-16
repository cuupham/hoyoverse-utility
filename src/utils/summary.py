"""GitHub job summary - bảng kết quả hiển thị đầu trang của run."""

from __future__ import annotations

import os

from src.models.game import Game
from src.models.results import CheckinResults
from src.utils.display import checkin_label, format_result_line

SUMMARY_PATH_ENV = "GITHUB_STEP_SUMMARY"


def build_summary(
    checkin_results: CheckinResults, failures: list[str], seconds: float
) -> str:
    lines = [f"### {format_result_line(checkin_results, failures, seconds)}", ""]
    if checkin_results:
        lines += [
            "| Account | " + " | ".join(game.value.name for game in Game) + " |",
            "|---" * (len(Game) + 1) + "|",
        ]
        lines += [
            f"| {account} | "
            + " | ".join(checkin_label(results[game], markdown=True) for game in Game)
            + " |"
            for account, results in checkin_results.items()
        ]
    if failures:
        lines += ["", *(f"- {failure}" for failure in failures)]
    return "\n".join(lines) + "\n"


def write_job_summary(
    checkin_results: CheckinResults, failures: list[str], seconds: float
) -> None:
    path = os.environ.get(SUMMARY_PATH_ENV)
    if not path:
        return
    # A summary that cannot be written must not change the run's exit code.
    try:
        with open(path, "a", encoding="utf-8") as summary:
            summary.write(build_summary(checkin_results, failures, seconds))
    except OSError:
        pass
