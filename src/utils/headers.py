"""Headers utility - Dynamic User-Agent generation"""
import re
from fake_useragent import UserAgent


def get_dynamic_headers() -> dict[str, str]:
    """Generate headers với User-Agent Chrome mới nhất
    
    Returns:
        Dict chứa user-agent và sec-ch-ua headers
    """
    ua = UserAgent()
    chrome_ua = ua.chrome
    
    # Parse version từ UA string: "Chrome/143.0.0.0" → "143"
    match = re.search(r'Chrome/(\d+)', chrome_ua)
    version = match.group(1) if match else "142"
    
    return {
        "user-agent": chrome_ua,
        "sec-ch-ua": f'"Chromium";v="{version}", "Google Chrome";v="{version}", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }


# Gọi 1 lần khi khởi động - cache kết quả
DYNAMIC_HEADERS = get_dynamic_headers()
