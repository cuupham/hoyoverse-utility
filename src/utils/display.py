"""Display utilities - Format và hiển thị kết quả check-in/redeem"""

from __future__ import annotations

from src.config import SYSTEM_MESSAGES
from src.models.game import Game
from src.models.types import CheckinResult, RedeemResult
from src.utils.logger import log_info, log_print

# Retcode cho "no in-game character detected" từ HoYoLab API
_RETCODE_NO_CHARACTER = -10002


def _plural(n: int, singular: str) -> str:
    """Trả về '1 code' hoặc '3 codes'."""
    return f"{n} {singular}" if n == 1 else f"{n} {singular}s"


# ==================== CHECK-IN ====================


def _short_checkin_status(result: CheckinResult) -> str:
    """Rút gọn status check-in cho table display."""
    if result["success"]:
        if SYSTEM_MESSAGES["CHECKIN_ALREADY"] in result["message"]:
            return SYSTEM_MESSAGES["CHECKIN_ALREADY_SHORT"]
        return f"✓ Ngày {result['day']}"

    # Ưu tiên retcode nếu có, fallback sang string matching
    if result.get("retcode") == _RETCODE_NO_CHARACTER:
        return SYSTEM_MESSAGES["CHECKIN_NO_CHARACTER"]
    msg = result["message"]
    if "character" in msg.lower():
        return SYSTEM_MESSAGES["CHECKIN_NO_CHARACTER"]
    return f"✗ {msg[:20]}"


def display_checkin(all_results: dict[str, dict[Game, CheckinResult]]) -> None:
    """Hiển thị kết quả check-in dạng table."""
    log_print(SYSTEM_MESSAGES["SECTION_CHECKIN"])

    games = list(Game)
    if not all_results:
        log_print()
        return
    acc_w = max(len("Account"), max(len(n) for n in all_results)) + 2
    col_w = 21

    header = f"{'Account':<{acc_w}}"
    for game in games:
        header += f"  {game.value.name:<{col_w}}"
    log_print(header)

    for acc_name, results in all_results.items():
        row = f"{acc_name:<{acc_w}}"
        for game in games:
            status = _short_checkin_status(results[game])
            row += f"  {status:<{col_w}}"
        log_print(row)
    log_print()


# ==================== REDEEM ====================


def display_cdkeys(cdkeys: dict[Game, list[str]]) -> None:
    """Hiển thị danh sách CDKeys đã fetch."""
    for game, codes in cdkeys.items():
        if codes:
            codes_str = ", ".join(codes)
            log_print(f"  {game.value.name}: {_plural(len(codes), 'code')} [{codes_str}]")
        else:
            log_print(f"  {game.value.name}: {SYSTEM_MESSAGES['SYSTEM_NO_CODES']}")


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
            log_print(f"  {acc_name}: {', '.join(uid_info)}")
        else:
            log_print(f"  {acc_name}: {SYSTEM_MESSAGES['SYSTEM_NO_UIDS']}")


def _short_redeem_status(res: RedeemResult) -> str:
    """Rút gọn status redeem cho table display."""
    if res.get("skipped"):
        return "⏭ Skip"
    if res.get("success"):
        return "✓ Thành công"
    return f"✗ {res.get('message', 'Error')}"


def display_redeem_results(results_map: dict[str, dict[Game, dict[str, dict[str, RedeemResult]]]]) -> None:
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
                res = codes_res.get(code, {})
                status = _short_redeem_status(res)
                if len(status) > code_w - 2:
                    status = status[: code_w - 4] + ".."
                row += f"{status:<{code_w}}"
            log_print(row)
            prev_acc = acc_name
    log_print()


def display_redeem(cdkeys: dict[Game, list[str]], account_uids: dict[str, dict[Game, dict[str, str]]]) -> None:
    """Hiển thị header redeem: CDKeys + UIDs (trước khi redeem bắt đầu)."""
    log_print(SYSTEM_MESSAGES["SECTION_REDEEM"])

    log_print(SYSTEM_MESSAGES["LABEL_CDKEYS"])
    display_cdkeys(cdkeys)

    total_codes = sum(len(codes) for codes in cdkeys.values())
    if total_codes == 0:
        log_info("SYSTEM", SYSTEM_MESSAGES["REDEEM_NO_CODES"])
        return

    log_print(SYSTEM_MESSAGES["LABEL_UIDS"])
    display_uids(account_uids)
    log_print()
