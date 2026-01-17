"""Helper functions - Các hàm tiện ích"""
import os
import time
from datetime import datetime


def current_hour() -> str:
    """Trả về giờ hiện tại dạng 2 chữ số (00-23)"""
    return f'{datetime.now().hour:02}'


def rpc_weekday() -> str:
    """Trả về thứ trong tuần (1=Monday, 7=Sunday)"""
    return str(datetime.now().isoweekday())


def unix_ms() -> int:
    """Trả về timestamp hiện tại dạng milliseconds"""
    return int(time.time() * 1000)


def get_accounts_from_env() -> dict[str, str]:
    """Lấy tất cả biến môi trường bắt đầu bằng ACC_
    
    Returns:
        Dict {name: cookie_string} cho các accounts tìm được
    """
    return {k: v for k, v in os.environ.items() if k.startswith('ACC_') and v.strip()}
