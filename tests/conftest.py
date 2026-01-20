"""Pytest fixtures và mock data cho testing"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any

from src.models.account import Account
from src.models.game import Game


# ==================== MOCK ACCOUNTS ====================
@pytest.fixture
def mock_account() -> Account:
    """Tạo mock account cho testing"""
    cookie_str = "ltoken_v2=mock_ltoken_v2; ltuid_v2=123456789; cookie_token_v2=mock_cookie_token; account_id_v2=123456789; _MHYUUID=mock-mhyuuid-1234; _HYVUUID=mock-hyvuuid-5678"
    return Account.from_env("TEST_ACC", cookie_str)


@pytest.fixture
def mock_accounts() -> list[Account]:
    """Tạo list mock accounts"""
    return [
        Account.from_env(
            "ACC_1",
            "ltoken_v2=mock_ltoken_1; ltuid_v2=111111111; cookie_token_v2=mock_cookie_1; account_id_v2=111111111; _MHYUUID=mock-mhyuuid-1111; _HYVUUID=mock-hyvuuid-1111"
        ),
        Account.from_env(
            "ACC_2",
            "ltoken_v2=mock_ltoken_2; ltuid_v2=222222222; cookie_token_v2=mock_cookie_2; account_id_v2=222222222; _MHYUUID=mock-mhyuuid-2222; _HYVUUID=mock-hyvuuid-2222"
        ),
    ]



# ==================== MOCK CDKEYS ====================
@pytest.fixture
def mock_cdkeys_all_games() -> dict[Game, list[str]]:
    """Mock CDKeys cho tất cả games"""
    return {
        Game.GENSHIN: ["GENSHINGIFT2024", "WELKINCODE123", "PRIMOGEMS500"],
        Game.STAR_RAIL: ["HSRGIFT2024", "STELLARJADE100", "RAILPASS999"],
        Game.ZZZ: ["ZZZGIFT2024", "POLYCHROME200", "BANGBOO666"],
    }


@pytest.fixture
def mock_cdkeys_partial() -> dict[Game, list[str]]:
    """Mock CDKeys - chỉ có 1 số games"""
    return {
        Game.GENSHIN: ["GENSHINGIFT2024"],
        Game.STAR_RAIL: [],
        Game.ZZZ: ["ZZZGIFT2024", "POLYCHROME200"],
    }


@pytest.fixture
def mock_cdkeys_empty() -> dict[Game, list[str]]:
    """Mock CDKeys - không có codes nào"""
    return {
        Game.GENSHIN: [],
        Game.STAR_RAIL: [],
        Game.ZZZ: [],
    }


@pytest.fixture
def mock_cdkeys_invalid() -> dict[Game, list[str]]:
    """Mock CDKeys - có codes không hợp lệ"""
    return {
        Game.GENSHIN: ["EXPIREDCODE001", "INVALIDXXX123", "USEDCODE999"],
        Game.STAR_RAIL: ["ALREADYREDEEMED"],
        Game.ZZZ: [],
    }


# ==================== MOCK UIDS ====================
@pytest.fixture
def mock_uids_all_regions() -> dict[Game, dict[str, str]]:
    """Mock UIDs cho tất cả regions"""
    return {
        Game.GENSHIN: {
            "os_asia": "800000001",
            "os_usa": "600000001",
            "os_euro": "700000001",
            "os_cht": "900000001",
        },
        Game.STAR_RAIL: {
            "prod_official_asia": "1300000001",
            "prod_official_usa": "1500000001",
            "prod_official_euro": "1700000001",
            "prod_official_cht": "1900000001",
        },
        Game.ZZZ: {
            "prod_gf_jp": "1000000001",
            "prod_gf_us": "1100000001",
            "prod_gf_eu": "1200000001",
            "prod_gf_sg": "1300000001",
        },
    }


@pytest.fixture
def mock_uids_partial() -> dict[Game, dict[str, str]]:
    """Mock UIDs - chỉ có 1 số games/regions"""
    return {
        Game.GENSHIN: {"os_asia": "800000001"},
        Game.STAR_RAIL: {},
        Game.ZZZ: {"prod_gf_jp": "1000000001", "prod_gf_us": "1100000001"},
    }


@pytest.fixture
def mock_uids_empty() -> dict[Game, dict[str, str]]:
    """Mock UIDs - không có UID nào"""
    return {
        Game.GENSHIN: {},
        Game.STAR_RAIL: {},
        Game.ZZZ: {},
    }


# ==================== MOCK API RESPONSES ====================
@pytest.fixture
def mock_check_cookie_success() -> dict[str, Any]:
    """Mock response - check cookie thành công"""
    return {
        "success": True,
        "data": {
            "retcode": 0,
            "message": "OK",
            "data": {"email_mask": "c****u9991@gmail.com"}
        }
    }


@pytest.fixture
def mock_check_cookie_invalid() -> dict[str, Any]:
    """Mock response - cookie hết hạn"""
    return {
        "success": True,
        "data": {
            "retcode": -100,
            "message": "Please login",
            "data": None
        }
    }


@pytest.fixture
def mock_checkin_info_not_signed() -> dict[str, Any]:
    """Mock response - chưa điểm danh"""
    return {
        "success": True,
        "data": {
            "retcode": 0,
            "message": "OK",
            "data": {
                "total_sign_day": 10,
                "is_sign": False,
                "today": "2026-01-18"
            }
        }
    }


@pytest.fixture
def mock_checkin_info_signed() -> dict[str, Any]:
    """Mock response - đã điểm danh"""
    return {
        "success": True,
        "data": {
            "retcode": 0,
            "message": "OK",
            "data": {
                "total_sign_day": 11,
                "is_sign": True,
                "today": "2026-01-18"
            }
        }
    }


@pytest.fixture
def mock_checkin_sign_success() -> dict[str, Any]:
    """Mock response - điểm danh POST thành công"""
    return {
        "success": True,
        "data": {
            "retcode": 0,
            "message": "OK",
            "data": {"code": "", "risk_code": 0}
        }
    }


@pytest.fixture
def mock_checkin_no_character() -> dict[str, Any]:
    """Mock response - không có nhân vật"""
    return {
        "success": True,
        "data": {
            "retcode": -10002,
            "message": "No in-game character detected",
            "data": None
        }
    }


# Format: safe_api_call returns {"success": True, "data": <api_response>}
@pytest.fixture
def mock_redeem_success() -> dict[str, Any]:
    """Mock response - redeem thành công"""
    return {
        "success": True,
        "data": {
            "retcode": 0,
            "message": "OK",
            "data": None,
        }
    }


@pytest.fixture
def mock_redeem_already_claimed() -> dict[str, Any]:
    """Mock response - đã nhận rồi"""
    return {
        "success": True,
        "data": {
            "retcode": -2017,
            "message": "Redemption code has been used",
            "data": None,
        }
    }


@pytest.fixture
def mock_redeem_expired() -> dict[str, Any]:
    """Mock response - code hết hạn"""
    return {
        "success": True,
        "data": {
            "retcode": -2001,
            "message": "Redemption code has expired",
            "data": None,
        }
    }


@pytest.fixture
def mock_redeem_invalid() -> dict[str, Any]:
    """Mock response - code không hợp lệ"""
    return {
        "success": True,
        "data": {
            "retcode": -2003,
            "message": "Invalid redemption code",
            "data": None,
        }
    }


@pytest.fixture
def mock_redeem_cooldown() -> dict[str, Any]:
    """Mock response - cooldown quá nhanh"""
    return {
        "success": True,
        "data": {
            "retcode": -2016,
            "message": "Redemption in cooldown",
            "data": None,
        }
    }


@pytest.fixture
def mock_redeem_low_rank() -> dict[str, Any]:
    """Mock response - chưa đủ rank (Adventure Rank < 10, etc.)"""
    return {
        "success": True,
        "data": {
            "retcode": -2011,
            "message": "You do not meet the Adventure Rank requirements",
            "data": None,
        }
    }


# ==================== MOCK SESSION ====================
@pytest.fixture
def mock_session() -> AsyncMock:
    """Tạo mock aiohttp session"""
    session = AsyncMock()
    session.get = AsyncMock()
    session.post = AsyncMock()
    return session
