"""GitHub job summary - bảng kết quả hiển thị đầu trang của run."""

from __future__ import annotations

import os
import re

from src.models.game import Game
from src.models.results import CheckinResults
from src.utils.display import checkin_label, format_result_line

SUMMARY_PATH_ENV = "GITHUB_STEP_SUMMARY"


def _code_span(text: str) -> str:
    """Render text literally: no links, images, HTML or autolinks in the summary.

    Failure lines embed provider-controlled messages, so they must not be parsed
    as Markdown. The fence is longer than any backtick run inside the text.
    """
    runs = [len(part) for part in re.findall(r"`+", text)]
    longest = max(runs, default=0)
    fence = "`" * (longest + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


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
        lines += ["", *(f"- {_code_span(failure)}" for failure in failures)]
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
