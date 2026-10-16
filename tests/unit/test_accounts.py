"""Tests grouped by their implementation owner."""

import pytest

from src.models.account import Account


class TestAccountModel:
    """Test cases cho Account model"""

    def test_account_from_cookie_string_success(self):
        """Test tạo account thành công từ cookie string"""
        cookie = "ltoken_v2=v2; ltuid_v2=123; cookie_token_v2=c2; account_id_v2=456; _MHYUUID=m1; _HYVUUID=h1"
        acc = Account.from_cookie_string("ACC_1", cookie)
        assert acc.name == "ACC_1"
        assert acc.cookies["ltoken_v2"] == "v2"
        assert acc.mhy_uuid == "m1"

    def test_account_from_cookie_string_missing_keys(self):
        """Test lỗi khi thiếu required keys"""
        cookie = "ltoken_v2=v2; ltuid_v2=123"
        with pytest.raises(ValueError) as excinfo:
            Account.from_cookie_string("BAD_ACC", cookie)
        assert "Missing required cookies" in str(excinfo.value)

    def test_account_cookies_immutable(self):
        """Test cookies dict thực sự immutable (MappingProxyType)"""
        cookie = "ltoken_v2=v2; ltuid_v2=123; cookie_token_v2=c2; account_id_v2=456; _MHYUUID=m1; _HYVUUID=h1"
        acc = Account.from_cookie_string("ACC_1", cookie)
        with pytest.raises(TypeError):
            acc.cookies["new_key"] = "should_fail"


class TestAccountEdgeCases:
    def test_empty_cookie_string(self):
        with pytest.raises(ValueError, match="empty"):
            Account.from_cookie_string("ACC", "")

    def test_whitespace_only_cookie(self):
        with pytest.raises(ValueError, match="empty"):
            Account.from_cookie_string("ACC", "   ")

    def test_cookie_pair_without_equals(self):
        """Pairs như 'justvalue' bị skip"""
        cookie = "justvalue; _MHYUUID=m; _HYVUUID=h; cookie_token_v2=c; account_id_v2=a"
        acc = Account.from_cookie_string("ACC", cookie)
        assert "justvalue" not in acc.cookies

    def test_frozen_dataclass(self):
        cookie = "_MHYUUID=m; _HYVUUID=h; cookie_token_v2=c; account_id_v2=a"
        acc = Account.from_cookie_string("ACC", cookie)
        with pytest.raises(AttributeError):
            acc.name = "new_name"
