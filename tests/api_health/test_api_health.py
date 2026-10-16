"""API Health Check - Kiểm tra các endpoints HoYoLab còn sống

Chạy: pytest tests/api_health/ -m live
Yêu cầu: Cookie thật trong env (ACC_*) hoặc tests/auth/.env.ps1

Mục đích:
- Phát hiện sớm khi HoYoverse thay đổi/kill endpoints
- Verify cấu trúc response vẫn đúng format mà code expect
- Không thực hiện hành động nào thay đổi state (không checkin, không redeem thật)
"""

import pytest

from src.api.checkin import check_cookie, get_checkin_info
from src.api.redeem_fetch import fetch_all_uids, fetch_cdkeys
from src.config import RETCODE_NO_CHARACTER
from src.models.game import Game

# Tất cả tests trong file này đều cần marker live
pytestmark = pytest.mark.live


class TestCookieValidationEndpoint:
    """Kiểm tra endpoint: bbs-api-os.hoyolab.com/community/misc/wapi/account/user_brief_info"""

    @pytest.mark.asyncio
    async def test_cookie_valid_returns_email_mask(self, live_session, live_account):
        """Cookie hợp lệ → retcode 0 + email_mask"""
        result = await check_cookie(live_session, live_account)

        assert result["valid"] is True, f"Cookie không hợp lệ: {result.get('error')}"
        assert result["email_mask"] is not None, "API không trả email_mask"
        assert "*" in result["email_mask"], "API should mask the email"
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_multi_account_validation(self, live_session, live_accounts):
        """Tất cả accounts đều validate được"""
        for acc in live_accounts:
            result = await check_cookie(live_session, acc)
            assert (
                result["valid"] is True
            ), f"{acc.name}: Cookie invalid - {result.get('error')}"


class TestCheckinInfoEndpoints:
    """Kiểm tra endpoints: checkin_info cho 3 games (GET, read-only)

    Endpoints:
    - sg-act-public-api.hoyolab.com/event/sol/info (Genshin)
    - sg-act-public-api.hoyolab.com/event/luna/hkrpg/os/info (Star Rail)
    - sg-act-public-api.hoyolab.com/event/luna/zzz/os/info (ZZZ)
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("game", list(Game), ids=lambda g: g.value.code)
    async def test_checkin_info_responds(self, live_session, live_account, game):
        """Endpoint trả về JSON hợp lệ với is_sign và total_sign_day"""
        result = await get_checkin_info(live_session, live_account, game)

        # Nếu account không chơi game này → error "No character" là valid response
        if result.get("retcode") == RETCODE_NO_CHARACTER:
            pytest.skip(f"{live_account.name} không chơi {game.value.name}")

        assert (
            result["error"] is None
        ), f"{game.value.name}: API error - {result['error']}"
        assert isinstance(result["is_sign"], bool), "is_sign phải là bool"
        assert isinstance(result["total_sign_day"], int), "total_sign_day phải là int"
        assert result["total_sign_day"] >= 0, "total_sign_day không thể âm"


class TestCDKeyFetchEndpoint:
    """Kiểm tra endpoint: bbs-api-os.hoyolab.com/.../guide/material

    Endpoint này trả danh sách redeem codes công khai, không cần auth mạnh.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("game", list(Game), ids=lambda g: g.value.code)
    async def test_cdkey_fetch_responds(self, live_session, live_account, game):
        """Endpoint trả list (có thể rỗng nếu không có codes)"""
        result = await fetch_cdkeys(live_session, live_account, game)
        assert result.success, result.error
        codes = result.data

        # Kết quả phải là list (rỗng OK, nhưng phải là list)
        assert isinstance(
            codes, list
        ), f"{game.value.name}: Expected list, got {type(codes)}"

        # Nếu có codes → mỗi code phải là string không rỗng
        for code in codes:
            assert isinstance(code, str) and len(code) > 0, f"Code format lạ: {code!r}"


class TestUIDFetchEndpoint:
    """Kiểm tra endpoint: api-account-os.hoyolab.com/binding/api/getUserGameRolesByLtoken

    fetch_all_uids dùng 1 request trả mọi game role rồi map ngược về (Game, region_code).
    """

    @pytest.mark.asyncio
    async def test_uid_fetch_responds_with_valid_format(
        self, live_session, live_account
    ):
        """Endpoint trả UID hợp lệ (chuỗi số ≥6) cho mọi role tìm được."""
        result = await fetch_all_uids(live_session, live_account)
        assert result.success, result.error
        all_uids = result.data

        assert isinstance(all_uids, dict)
        assert set(all_uids.keys()) == set(Game), "Phải có key cho cả 3 games"

        for game, regions in all_uids.items():
            for region_code, uid in regions.items():
                assert (
                    uid.isdigit()
                ), f"{game.value.name}/{region_code}: UID must contain digits"
                assert len(uid) >= 6, f"{game.value.name}/{region_code}: UID too short"


class TestEndpointResponseTime:
    """Kiểm tra response time - phát hiện degradation"""

    @pytest.mark.asyncio
    async def test_cookie_check_under_10s(self, live_session, live_account):
        """Cookie validation phải respond trong 10s"""
        import time

        start = time.monotonic()
        result = await check_cookie(live_session, live_account)
        elapsed = time.monotonic() - start

        assert result["valid"] is True, f"Cookie invalid: {result.get('error')}"
        assert elapsed < 10, f"Cookie check quá chậm: {elapsed:.1f}s (limit 10s)"

    @pytest.mark.asyncio
    async def test_cdkey_fetch_under_10s(self, live_session, live_account):
        """CDKey fetch phải respond trong 10s"""
        import time

        start = time.monotonic()
        result = await fetch_cdkeys(live_session, live_account, Game.GENSHIN)
        elapsed = time.monotonic() - start

        assert result.success, result.error
        assert elapsed < 10, f"CDKey fetch quá chậm: {elapsed:.1f}s (limit 10s)"
