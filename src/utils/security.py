"""Security utilities - Mask sensitive data"""
from src.config import MIN_UID_LENGTH


def mask_uid(uid: str | int | None) -> str:
    """Mask UID: 123456789 → 123***789
    
    Args:
        uid: UID của player (string hoặc int)
        
    Returns:
        Masked UID string
    """
    if not uid:
        return "***"
    uid = str(uid)
    if len(uid) <= MIN_UID_LENGTH:
        return "***"
    return f"{uid[:3]}***{uid[-3:]}"
