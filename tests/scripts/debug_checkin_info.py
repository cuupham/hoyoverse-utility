"""Read-only diagnostics using the same validated requests as the application."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Support direct execution from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.api.checkin import check_cookie, get_checkin_info
from src.api.client import create_session
from src.api.redeem_fetch import fetch_all_uids
from src.config import RETCODE_NO_CHARACTER
from src.models.game import Game
from tests.support.accounts import load_live_accounts


async def debug_checkin_info() -> int:
    try:
        accounts = load_live_accounts()
    except ValueError as error:
        print(error)
        return 1
    if not accounts:
        print("No accounts. Set ACC_* or tests/auth/.env.ps1")
        return 1
    failed = False
    async with create_session() as session:
        for account in accounts:
            validation = await check_cookie(session, account)
            print(f"{account.name}: {validation['status']}")
            if not validation["valid"]:
                print(validation["error"])
                failed = True
                continue
            roles = await fetch_all_uids(session, account)
            if not roles.success:
                print(f"Role discovery failed: {roles.error}")
                failed = True
            for game in Game:
                regions = list(roles.data.get(game, {}))
                print(f"{game.value.name}: regions={regions}")
                info = await get_checkin_info(session, account, game)
                print(json.dumps(info, ensure_ascii=True))
                failed = failed or bool(
                    info["error"] and info.get("retcode") != RETCODE_NO_CHARACTER
                )
    return int(failed)


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    raise SystemExit(asyncio.run(debug_checkin_info()))
