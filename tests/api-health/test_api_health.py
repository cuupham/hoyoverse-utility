"""API Health Check - Kiểm tra các endpoints HoYoLab còn sống

Chạy: pytest tests/api-health/ -m live
Yêu cầu: Cookie thật trong env (ACC_*) hoặc tests/auth/.env.ps1

Mục đích:
- Phát hiện sớm khi HoYoverse thay đổi/kill endpoints
- Verify cấu trúc response vẫn đúng format mà code expect
- Không thực hiện hành động nào thay đổi state (không checkin, không redeem thật)
"""

import pytest

from src.api.checkin import check_cookie, get_checkin_info
from src.api.redeem_fetch import fetch_cdkeys, fetch_uid
from src.api.redeem_exchange import exchange_cdkey
from src.models.game import Game, REGIONS

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
        assert "****" in result["email_mask"], f"email_mask format lạ: {result['email_mask']}"
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_multi_account_validation(self, live_session, live_accounts):
        """Tất cả accounts đều validate được"""
        for acc in live_accounts:
            result = await check_cookie(live_session, acc)
            assert result["valid"] is True, f"{acc.name}: Cookie invalid - {result.get('error')}"


class TestCheckinInfoEndpoints:
    """Kiểm tra endpoints: checkin_info cho 3 games (GET, read-only)

    Endpoints:
    - sg-hk4e-api.hoyolab.com/event/sol/info (Genshin)
    - sg-public-api.hoyolab.com/event/luna/hkrpg/os/info (Star Rail)
    - sg-public-api.hoyolab.com/event/luna/zzz/os/info (ZZZ)
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("game", list(Game), ids=lambda g: g.value.code)
    async def test_checkin_info_responds(self, live_session, live_account, game):
        """Endpoint trả về JSON hợp lệ với is_sign và total_sign_day"""
        result = await get_checkin_info(live_session, live_account, game)

        # Nếu account không chơi game này → error "No character" là valid response
        if result["error"] and "character" in str(result["error"]).lower():
            pytest.skip(f"{live_account.name} không chơi {game.value.name}")

        assert result["error"] is None, f"{game.value.name}: API error - {result['error']}"
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
        codes = await fetch_cdkeys(live_session, live_account, game)

        # Kết quả phải là list (rỗng OK, nhưng phải là list)
        assert isinstance(codes, list), f"{game.value.name}: Expected list, got {type(codes)}"

        # Nếu có codes → mỗi code phải là string không rỗng
        for code in codes:
            assert isinstance(code, str) and len(code) > 0, f"Code format lạ: {code!r}"

    @pytest.mark.asyncio
    async def test_cdkey_fetch_returns_known_structure(self, live_session, live_account):
        """Ít nhất 1 game nên có codes (trừ khi đúng lúc không có event)"""
        total_codes = 0
        for game in Game:
            codes = await fetch_cdkeys(live_session, live_account, game)
            total_codes += len(codes)

        # Soft assertion - warn thay vì fail vì có thể đúng lúc không có codes
        if total_codes == 0:
            pytest.skip("Không có codes nào ở thời điểm test - có thể bình thường")


class TestUIDFetchEndpoint:
    """Kiểm tra endpoint: api-account-os.hoyolab.com/binding/api/getUserGameRolesByLtoken"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("game", list(Game), ids=lambda g: g.value.code)
    async def test_uid_fetch_responds(self, live_session, live_account, game):
        """Endpoint trả UID cho ít nhất 1 region (nếu account chơi game đó)"""
        found_any = False

        for region_code in REGIONS[game]:
            uid = await fetch_uid(live_session, live_account, game, region_code)
            if uid:
                found_any = True
                # UID phải là chuỗi số hợp lệ
                assert uid.isdigit(), f"UID format lạ: {uid!r}"
                assert len(uid) >= 6, f"UID quá ngắn: {uid}"

        if not found_any:
            pytest.skip(f"{live_account.name} không chơi {game.value.name}")

    @pytest.mark.asyncio
    async def test_uid_fetch_at_least_one_game(self, live_session, live_account):
        """Account phải có UID cho ít nhất 1 game"""
        total_uids = 0
        for game in Game:
            for region_code in REGIONS[game]:
                uid = await fetch_uid(live_session, live_account, game, region_code)
                if uid:
                    total_uids += 1

        assert total_uids > 0, f"{live_account.name}: Không tìm thấy UID nào - account có thể chưa tạo nhân vật"


class TestRedeemEndpoint:
    """Kiểm tra endpoint: public-operation-*.hoyolab.com/.../webExchangeCdkeyHyl

    Dùng INVALID code cố ý để test endpoint còn respond mà KHÔNG redeem thật.
    Expected: retcode -2001 (code không tồn tại) hoặc -2003 (code đã sử dụng).
    """

    # Code giả - chắc chắn không hợp lệ, dùng để probe endpoint
    _PROBE_CODE = "HEALTHCHECK000INVALID"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("game", list(Game), ids=lambda g: g.value.code)
    async def test_redeem_endpoint_responds(self, live_session, live_account, game):
        """Endpoint trả retcode cho invalid code (chứng minh endpoint sống)"""
        # Tìm UID đầu tiên cho game này
        uid = None
        region = None
        for region_code in REGIONS[game]:
            uid = await fetch_uid(live_session, live_account, game, region_code)
            if uid:
                region = region_code
                break

        if not uid:
            pytest.skip(f"{live_account.name} không chơi {game.value.name}")

        result = await exchange_cdkey(
            live_session, live_account, game, region, uid, self._PROBE_CODE
        )

        # Endpoint sống = trả về response (dù là lỗi code invalid)
        assert result["success"] is False, "Code giả không nên thành công!"
        assert result["message"], "Phải có error message"

        # retcode phải là known error (-2001, -2003, -2016, etc.)
        retcode = result.get("retcode")
        if retcode is not None:
            assert retcode != 0, "Code giả không nên trả retcode 0"


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
        await fetch_cdkeys(live_session, live_account, Game.GENSHIN)
        elapsed = time.monotonic() - start

        assert elapsed < 10, f"CDKey fetch quá chậm: {elapsed:.1f}s (limit 10s)"
