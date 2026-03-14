"""HTTP Client - Retry logic, semaphore, và error handling

SECURITY WARNING: Never log cookies or sensitive headers.
The 'headers' dict passed to safe_api_call contains cookies - do not log it directly.
"""

import asyncio
import random  # nosec B311 - used for anti-detection jitter, not cryptography
from typing import Any

import aiohttp

from src.config import (
    CONNECTOR_LIMIT,
    CONNECTOR_LIMIT_PER_HOST,
    CONNECT_TIMEOUT,
    MAX_RETRIES,
    MIN_REQUEST_TIMEOUT,
    RATE_LIMIT_DELAY,
    REQUEST_TIMEOUT,
    SEMAPHORE_LIMIT,
    SYSTEM_MESSAGES,
)

# HTTP status codes that should trigger retry (transient server errors)
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Lazy semaphore - tạo khi cần, gắn đúng event loop
_SEMAPHORE: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    """Lazy initialization để semaphore gắn đúng event loop hiện tại

    Tại sao cần lazy?
    - Nếu tạo ở module scope, semaphore có thể gắn sai event loop
    - Lazy init đảm bảo tạo khi asyncio.run() đã chạy
    - Hỗ trợ testing với nhiều event loops
    """
    global _SEMAPHORE
    if _SEMAPHORE is None:
        _SEMAPHORE = asyncio.Semaphore(SEMAPHORE_LIMIT)
    return _SEMAPHORE


def reset_semaphore() -> None:
    """Reset semaphore global state - dùng cho testing hoặc khi cần reinitialize."""
    global _SEMAPHORE
    _SEMAPHORE = None


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


async def safe_api_call(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict,
    params: dict | None = None,
    json_data: dict | None = None,
    method: str = "GET",
    max_retries: int = MAX_RETRIES,
) -> dict[str, Any]:
    """Pattern xử lý exception cho tất cả API calls với retry

    Args:
        session: aiohttp ClientSession
        url: URL to call
        headers: Request headers (contains cookies - never log this)
        params: Query params (for GET)
        json_data: JSON body (for POST)
        method: HTTP method
        max_retries: Số lần retry tối đa

    Returns:
        Dict với format {"success": bool, "data": ... hoặc "error": ..., "message": ...}
    """
    kwargs: dict[str, Any] = {"headers": headers}
    if params:
        kwargs["params"] = params
    if json_data:
        kwargs["json"] = json_data

    last_error: str = "Unknown error"

    for attempt in range(max_retries):
        try:
            # Per-attempt timeout giảm dần, nhưng không thấp hơn MIN_REQUEST_TIMEOUT
            remaining_attempts = max_retries - attempt
            attempt_timeout = aiohttp.ClientTimeout(
                total=max(REQUEST_TIMEOUT / remaining_attempts, MIN_REQUEST_TIMEOUT),
                connect=CONNECT_TIMEOUT,
            )
            kwargs["timeout"] = attempt_timeout

            async with _get_semaphore():
                # Anti-detection jitter (0.1s - 0.3s) bên trong semaphore
                # để không giữ slot khi chưa cần, và tránh request đồng thời
                await asyncio.sleep(random.uniform(0.1, 0.3))  # nosec B311
                async with session.request(method, url, **kwargs) as resp:
                    # Retry cho rate limit (429) và server errors (5xx)
                    if resp.status in _RETRYABLE_STATUS_CODES:
                        delay = RATE_LIMIT_DELAY if resp.status == 429 else 2**attempt
                        if attempt < max_retries - 1:
                            await asyncio.sleep(delay)
                            continue
                        last_error = f"HTTP {resp.status} after {max_retries} attempts"
                        return {"success": False, "error": "http_error", "message": last_error}

                    data = await resp.json()
                    return {"success": True, "data": data}

        except aiohttp.ClientConnectionError:
            last_error = SYSTEM_MESSAGES["ERR_NETWORK"]
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
                continue
            return {"success": False, "error": "network", "message": last_error}

        except asyncio.TimeoutError:
            last_error = SYSTEM_MESSAGES["ERR_TIMEOUT"]
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
                continue
            return {"success": False, "error": "timeout", "message": last_error}

        except aiohttp.ContentTypeError:
            return {"success": False, "error": "invalid_json", "message": SYSTEM_MESSAGES["ERR_INVALID_JSON"]}

        except Exception as e:
            last_error = _sanitize_error_message(e)
            return {"success": False, "error": "unknown", "message": last_error}

    # All retries exhausted
    return {"success": False, "error": "max_retries", "message": f"Failed after {max_retries} attempts: {last_error}"}


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
            total=REQUEST_TIMEOUT,
            connect=CONNECT_TIMEOUT,
        ),
    )
