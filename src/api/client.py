"""HTTP Client - Retry logic, semaphore, và error handling

SECURITY WARNING: Never log cookies or sensitive headers.
The 'headers' dict passed to request_json contains cookies - do not log it directly.
"""

import asyncio
import json
import random  # nosec B311 - used for request pacing, not cryptography
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping

import aiohttp

from src.config import (
    CONNECT_TIMEOUT_SECONDS,
    CONNECTOR_LIMIT,
    CONNECTOR_LIMIT_PER_HOST,
    MAX_ATTEMPTS,
    MIN_ATTEMPT_TIMEOUT_SECONDS,
    RATE_LIMIT_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    SEMAPHORE_LIMIT,
    SYSTEM_MESSAGES,
)
from src.models.results import HttpCallResult, ProviderResult

# HTTP status codes that should trigger retry (transient server errors)
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Lazy semaphore - tạo khi cần, gắn đúng event loop
_SEMAPHORE: asyncio.Semaphore | None = None
_SEMAPHORE_LOOP: asyncio.AbstractEventLoop | None = None


def _get_semaphore() -> asyncio.Semaphore:
    """Share request permits within the active event loop."""
    global _SEMAPHORE, _SEMAPHORE_LOOP
    loop = asyncio.get_running_loop()
    if _SEMAPHORE is None or _SEMAPHORE_LOOP is not loop:
        _SEMAPHORE = asyncio.Semaphore(SEMAPHORE_LIMIT)
        _SEMAPHORE_LOOP = loop
    return _SEMAPHORE


def reset_semaphore() -> None:
    """Reset request permits between isolated test executions."""
    global _SEMAPHORE, _SEMAPHORE_LOOP
    _SEMAPHORE = None
    _SEMAPHORE_LOOP = None


def _sanitize_error_message(error: Exception) -> str:
    """Sanitize error message để không leak sensitive info

    Args:
        error: Exception object

    Returns:
        Safe error message string
    """
    error_str = str(error)

    # Patterns có thể leak info
    sensitive_patterns = [
        "cookie",
        "token",
        "password",
        "secret",
        "key",
        "auth",
    ]

    # Check if error contains sensitive info
    error_lower = error_str.lower()
    for pattern in sensitive_patterns:
        if pattern in error_lower:
            return SYSTEM_MESSAGES["ERR_UNKNOWN_SECURE"]

    # Truncate long error messages
    if len(error_str) > 100:
        return error_str[:100] + "..."

    return error_str


def parse_provider_envelope(
    result: HttpCallResult, *, allow_null_data: bool = False
) -> ProviderResult[dict[str, Any]]:
    """Own provider envelope validation independently of HTTP transport."""
    if not result["success"]:
        return ProviderResult(
            {},
            error=result.get("message") or SYSTEM_MESSAGES["REQUEST_FAILED"],
            error_kind=result.get("error", "unknown"),
        )
    envelope = result.get("data")
    if not isinstance(envelope, dict) or type(envelope.get("retcode")) is not int:
        return ProviderResult(
            {},
            error=SYSTEM_MESSAGES["ERR_INVALID_RESPONSE"],
            error_kind="invalid_response",
        )
    retcode = envelope["retcode"]
    if retcode != 0:
        message = envelope.get("message")
        return ProviderResult(
            {},
            error=(
                message if isinstance(message, str) and message else f"Error {retcode}"
            ),
            retcode=retcode,
            error_kind="provider",
        )
    data = envelope.get("data")
    if data is None and allow_null_data:
        data = {}
    if not isinstance(data, dict):
        return ProviderResult(
            {},
            error=SYSTEM_MESSAGES["ERR_INVALID_RESPONSE"],
            retcode=0,
            error_kind="invalid_response",
        )
    return ProviderResult(data, retcode=0)


def _retry_after(value: str | None, default: float) -> float:
    """Respect Retry-After seconds or HTTP dates for safe read retries."""
    if not isinstance(value, str):
        return default
    try:
        if value.isascii() and value.isdigit():
            return float(value)
        date = parsedate_to_datetime(value)
        return max(0.0, (date - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError, OverflowError):
        return default


async def request_json(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict[str, str],
    params: Mapping[str, str | int] | None = None,
    json_data: dict[str, str] | None = None,
    method: str = "GET",
    max_attempts: int = MAX_ATTEMPTS,
    *,
    retry: bool = True,
) -> HttpCallResult:
    """Pattern xử lý exception cho tất cả API calls với retry

    Args:
        session: aiohttp ClientSession
        url: URL to call
        headers: Request headers (contains cookies - never log this)
        params: Query params (for GET)
        json_data: JSON body (for POST)
        method: HTTP method
        max_attempts: Total attempts, including the initial request

    Returns:
        Dict với format {"success": bool, "data": ... hoặc "error": ..., "message": ...}
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    kwargs: dict[str, Any] = {"headers": headers}
    if params:
        kwargs["params"] = params
    if json_data:
        kwargs["json"] = json_data

    # Some HoYoLAB GET routes mutate state; their callers explicitly disable retry.
    attempts = max_attempts if retry and method.upper() in {"GET", "HEAD"} else 1
    failure: HttpCallResult = {
        "success": False,
        "error": "unknown",
        "message": SYSTEM_MESSAGES["REQUEST_FAILED"],
    }
    for attempt in range(attempts):
        delay = 2**attempt
        try:
            # Keep the existing per-attempt timeout floor and configured limit.
            remaining_attempts = attempts - attempt
            attempt_timeout = aiohttp.ClientTimeout(
                total=max(
                    REQUEST_TIMEOUT_SECONDS / remaining_attempts,
                    MIN_ATTEMPT_TIMEOUT_SECONDS,
                ),
                connect=CONNECT_TIMEOUT_SECONDS,
            )
            kwargs["timeout"] = attempt_timeout

            await asyncio.sleep(random.uniform(0.1, 0.3))  # nosec B311
            async with _get_semaphore():
                async with session.request(method, url, **kwargs) as resp:
                    # Retry cho rate limit (429) và server errors (5xx)
                    if resp.status in _RETRYABLE_STATUS_CODES:
                        default_delay = (
                            RATE_LIMIT_DELAY_SECONDS if resp.status == 429 else delay
                        )
                        delay = _retry_after(
                            resp.headers.get("Retry-After"), default_delay
                        )
                        last_error = f"HTTP {resp.status} after {attempt + 1} attempts"
                        failure = {
                            "success": False,
                            "error": "http_error",
                            "message": last_error,
                            "status": resp.status,
                        }
                    elif not 200 <= resp.status < 300:
                        return {
                            "success": False,
                            "error": "http_error",
                            "message": f"HTTP {resp.status}",
                            "status": resp.status,
                        }
                    else:
                        data = await resp.json()
                        return {"success": True, "data": data, "status": resp.status}

        except (aiohttp.ClientConnectionError, aiohttp.ClientPayloadError):
            last_error = SYSTEM_MESSAGES["ERR_NETWORK"]
            failure = {"success": False, "error": "network", "message": last_error}

        except asyncio.TimeoutError:
            last_error = SYSTEM_MESSAGES["ERR_TIMEOUT"]
            failure = {"success": False, "error": "timeout", "message": last_error}

        except (aiohttp.ContentTypeError, json.JSONDecodeError):
            return {
                "success": False,
                "error": "invalid_json",
                "message": SYSTEM_MESSAGES["ERR_INVALID_JSON"],
            }

        except Exception as e:
            last_error = _sanitize_error_message(e)
            return {"success": False, "error": "unknown", "message": last_error}

        # Release both response and semaphore before waiting for the next attempt.
        if attempt == attempts - 1 or delay > REQUEST_TIMEOUT_SECONDS:
            return failure
        await asyncio.sleep(delay)
    return failure


def create_session() -> aiohttp.ClientSession:
    """Tạo ClientSession với connection pooling và timeout.

    Sử dụng DummyCookieJar để tránh rò rỉ cookie giữa các accounts
    khi chạy song song, vì chúng ta đã tự quản lý cookie trong header.
    """
    return aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(
            limit=CONNECTOR_LIMIT,
            limit_per_host=CONNECTOR_LIMIT_PER_HOST,
        ),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(
            total=REQUEST_TIMEOUT_SECONDS,
            connect=CONNECT_TIMEOUT_SECONDS,
        ),
    )
