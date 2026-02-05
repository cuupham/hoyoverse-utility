"""Headers utility - Dynamic User-Agent generation"""
import re
from fake_useragent import UserAgent

from src.constants import DEFAULT_CHROME_VERSION


def get_dynamic_headers() -> dict[str, str]:
    """Generate headers với User-Agent Chrome mới nhất.

    Returns:
        Dict chứa user-agent và sec-ch-ua headers.
    """
    ua = UserAgent()
    chrome_ua = ua.chrome

    match = re.search(r"Chrome/(\d+)", chrome_ua)
    version = match.group(1) if match else DEFAULT_CHROME_VERSION

    return {
        "user-agent": chrome_ua,
        "sec-ch-ua": f'"Chromium";v="{version}", "Google Chrome";v="{version}", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }


# Gọi 1 lần khi khởi động - cache kết quả
DYNAMIC_HEADERS = get_dynamic_headers()
