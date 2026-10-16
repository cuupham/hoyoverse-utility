"""Clock values shared by CLI output and provider request metadata."""

import time
from datetime import datetime
from zoneinfo import ZoneInfo

from src.config import DEFAULT_TIMEZONE

TZ = ZoneInfo(DEFAULT_TIMEZONE)


def current_hour() -> str:
    return f"{datetime.now(TZ).hour:02}"


def rpc_weekday() -> str:
    return str(datetime.now(TZ).isoweekday())


def unix_ms() -> int:
    return int(time.time() * 1000)
