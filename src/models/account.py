"""Account model - Đại diện cho một tài khoản HoYoLab"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

# Required keys để đảm bảo cookie hoạt động
REQUIRED_COOKIE_KEYS = ["_MHYUUID", "_HYVUUID", "cookie_token_v2", "account_id_v2"]


@dataclass(frozen=True)
class Account:
    """Account dataclass - truly immutable, thread-safe.

    cookies sử dụng MappingProxyType để đảm bảo immutability hoàn toàn,
    vì frozen=True chỉ ngăn reassign attribute, không ngăn mutate dict.
    """

    name: str
    cookie_str: str
    cookies: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    @classmethod
    def from_env(cls, name: str, cookie_str: str) -> "Account":
        """Parse cookie string thành Account object.

        Raises:
            ValueError: Nếu cookie rỗng hoặc thiếu required keys.
        """
        if not cookie_str or not cookie_str.strip():
            raise ValueError(f"{name}: Cookie string is empty")

        # Parse cookie string
        cookies: dict[str, str] = {}
        for pair in cookie_str.split(";"):
            pair = pair.strip()
            if "=" in pair:
                key, value = pair.split("=", 1)
                cookies[key.strip()] = value.strip()

        # Kiểm tra required keys
        missing = [k for k in REQUIRED_COOKIE_KEYS if k not in cookies]
        if missing:
            raise ValueError(f"{name}: Missing required cookies: {missing}")

        return cls(name=name, cookie_str=cookie_str, cookies=MappingProxyType(cookies))

    @property
    def mhy_uuid(self) -> str:
        """Trả về _MHYUUID cho x-rpc-device_id"""
        return self.cookies.get("_MHYUUID", "")

    @property
    def hyv_uuid(self) -> str:
        """Trả về _HYVUUID cho một số API sign"""
        return self.cookies.get("_HYVUUID", "")
