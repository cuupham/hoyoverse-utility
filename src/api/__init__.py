# API modules
"""API modules for HoYoLab interactions

Avoid eager imports to prevent circular dependencies.
Use direct imports: from src.api.client import create_session
"""

__all__ = [
    # Client
    "create_session",
    "safe_api_call",
    # Check-in
    "check_cookie",
    "run_checkin_for_account",
    # Redeem
    "fetch_all_cdkeys",
    "fetch_all_uids",
    "run_redeem_for_account",
]
