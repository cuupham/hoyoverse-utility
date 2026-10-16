"""Display utilities - Format và hiển thị kết quả check-in/redeem"""

from __future__ import annotations

from src.config import (
    CHECKIN_LABELS,
    STATUS_ERROR,
    SYSTEM_MESSAGES,
    VERDICT_FAILED,
    VERDICT_OK,
)
from src.models.game import Game
from src.models.results import CheckinResult, CheckinResults, RedeemResult
from src.utils.logger import log_error, log_print

INDENT = "  "


def _plural(n: int, singular: str) -> str:
    """Trả về '1 code' hoặc '3 codes'."""
    return f"{n} {singular}" if n == 1 else f"{n} {singular}s"


# ==================== CHECK-IN ====================


def checkin_label(result: CheckinResult, *, markdown: bool = False) -> str:
    """Cell của check-in; job summary thêm icon phía trước."""
    text, icon = CHECKIN_LABELS[result["status"]]
    label = text.format(day=result.get("day"))
    return f"{icon} {label}" if markdown else label


def display_checkin(all_results: CheckinResults) -> None:
    """Hiển thị kết quả check-in dạng table."""
    log_print(SYSTEM_MESSAGES["SECTION_CHECKIN"])

    games = list(Game)
    if not all_results:
        log_print()
        return
    rows = {
        acc_name: [checkin_label(results[game]) for game in games]
        for acc_name, results in all_results.items()
    }
    acc_w = max(len("Account"), max(len(name) for name in rows)) + 2
    col_w = (
        max(
            max(len(game.value.short_name) for game in games),
            max(len(cell) for cells in rows.values() for cell in cells),
        )
        + 2
    )

    header = f"{INDENT}{'Account':<{acc_w}}"
    for game in games:
        header += f"{game.value.short_name:<{col_w}}"
    log_print(header.rstrip())
    for acc_name, cells in rows.items():
        row = f"{INDENT}{acc_name:<{acc_w}}" + "".join(f"{c:<{col_w}}" for c in cells)
        log_print(row.rstrip())
    log_print()


# ==================== RESULT ====================


def format_result_line(
    checkin_results: CheckinResults, failures: list[str], seconds: float
) -> str:
    statuses = [
        result["status"]
        for games in checkin_results.values()
        for result in games.values()
    ]
    return SYSTEM_MESSAGES["RESULT_LINE"].format(
        verdict=VERDICT_FAILED if failures else VERDICT_OK,
        ok=sum(status in {"claimed", "already_claimed"} for status in statuses),
        skipped=statuses.count("no_character"),
        errors=len(failures),
        seconds=seconds,
    )


def display_failures(failures: list[str]) -> None:
    for failure in failures:
        log_error(SYSTEM_MESSAGES["FAILURE_SCOPE"], failure)


def display_result(
    checkin_results: CheckinResults, failures: list[str], seconds: float
) -> None:
    display_failures(failures)
    log_print(format_result_line(checkin_results, failures, seconds))


# ==================== REDEEM ====================


def display_cdkeys(cdkeys: dict[Game, list[str]]) -> None:
    """Hiển thị danh sách CDKeys đã fetch."""
    for game, codes in cdkeys.items():
        if codes:
            codes_str = ", ".join(codes)
            log_print(
                f"{INDENT}{game.value.name}: {_plural(len(codes), 'code')} [{codes_str}]"
            )
        else:
            log_print(
                f"{INDENT}{game.value.name}: {SYSTEM_MESSAGES['SYSTEM_NO_CODES']}"
            )


def display_uids(account_uids: dict[str, dict[Game, dict[str, str]]]) -> None:
    """Hiển thị danh sách UIDs tìm thấy."""
    for acc_name, uids in account_uids.items():
        uid_info = []
        for game in Game:
            game_uids = uids.get(game, {})
            if game_uids:
                regions = ", ".join(game_uids.keys())
                uid_info.append(f"{game.value.name}({regions})")

        if uid_info:
            log_print(f"{INDENT}{acc_name}: {', '.join(uid_info)}")
        else:
            log_print(f"{INDENT}{acc_name}: {SYSTEM_MESSAGES['SYSTEM_NO_UIDS']}")


def _short_redeem_status(res: RedeemResult) -> str:
    """Rút gọn status redeem cho table display."""
    if res.get("success"):
        return SYSTEM_MESSAGES["REDEEM_SUCCESS"]
    retcode = res.get("retcode")
    prefix = f"[{retcode}] " if retcode is not None else ""
    return f"{STATUS_ERROR} {prefix}{res.get('message', 'Error')}"


def display_redeem_results(
    results_map: dict[str, dict[Game, dict[str, dict[str, RedeemResult]]]],
) -> None:
    """Hiển thị kết quả redeem dạng table, nhóm theo game."""
    # Tổ chức lại: game → [(acc, region, {code: result})]
    game_rows: dict[Game, list[tuple[str, str, dict[str, RedeemResult]]]] = {}
    for acc_name, game_results in results_map.items():
        for game, regions in game_results.items():
            for region, codes_res in regions.items():
                game_rows.setdefault(game, []).append((acc_name, region, codes_res))

    if not game_rows:
        return

    for game, rows in game_rows.items():
        # Collect tất cả unique codes từ mọi rows (giữ thứ tự xuất hiện)
        codes: list[str] = []
        seen: set[str] = set()
        for _, _, codes_res in rows:
            for code in codes_res:
                if code not in seen:
                    codes.append(code)
                    seen.add(code)

        # Tính column widths
        acc_w = max(7, max(len(r[0]) for r in rows)) + 2
        reg_w = max(6, max(len(r[1]) for r in rows)) + 2
        code_w = max(max(len(c) for c in codes), 14) + 2

        # Game header
        log_print(f"[{game.value.name}]")

        # Table header
        header = f"{'Account':<{acc_w}}{'Region':<{reg_w}}"
        for code in codes:
            header += f"{code:<{code_w}}"
        log_print(header)

        # Table rows — ẩn account name khi trùng row trước
        prev_acc = ""
        for acc_name, region, codes_res in rows:
            display_acc = acc_name if acc_name != prev_acc else ""
            row = f"{display_acc:<{acc_w}}{region:<{reg_w}}"
            for code in codes:
                res: RedeemResult = codes_res.get(code) or RedeemResult(
                    success=False, message=""
                )
                status = _short_redeem_status(res)
                if len(status) > code_w - 2:
                    status = status[: code_w - 4] + ".."
                row += f"{status:<{code_w}}"
            log_print(row)
            prev_acc = acc_name
    log_print()


def display_redeem(
    cdkeys: dict[Game, list[str]],
    account_uids: dict[str, dict[Game, dict[str, str]]],
    errors: list[str] | None = None,
) -> None:
    """Hiển thị đầu phần redeem: CDKeys + UIDs (trước khi redeem bắt đầu)."""
    if not any(cdkeys.values()):
        log_print(SYSTEM_MESSAGES["REDEEM_FETCH_FAILED" if errors else "REDEEM_NONE"])
        log_print()
        return

    log_print(SYSTEM_MESSAGES["SECTION_REDEEM"])
    display_cdkeys(cdkeys)
    log_print(SYSTEM_MESSAGES["LABEL_UIDS"])
    display_uids(account_uids)
    log_print()
