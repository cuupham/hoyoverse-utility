"""Shared transport, provider and application outcomes (Python 3.10 compatible)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, TypedDict, TypeVar

from src.models.game import Game

if TYPE_CHECKING:
    from src.models.account import Account

T = TypeVar("T")
ErrorKind = Literal[
    "network",
    "timeout",
    "http_error",
    "invalid_json",
    "invalid_response",
    "unknown",
    "provider",
]
CheckinStatus = Literal[
    "claimed", "already_claimed", "no_character", "challenge", "failed"
]
CookieStatus = Literal["valid", "invalid_credentials", "check_failed"]


@dataclass(frozen=True)
class ProviderResult(Generic[T]):
    """Successful empty data differs from a failed provider operation."""

    data: T
    error: str | None = None
    retcode: int | None = None
    error_kind: ErrorKind | None = None

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class RedemptionData:
    """Usable redemption inputs and unrecovered fetch failures."""

    cdkeys: dict[Game, list[str]]
    account_uids: dict[str, dict[Game, dict[str, str]]]
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AccountValidationResult:
    valid_accounts: list[Account]
    errors: list[str] = field(default_factory=list)


class _HttpRequired(TypedDict):
    success: bool


class HttpCallResult(_HttpRequired, total=False):
    """HTTP/JSON transport outcome; data is the unparsed provider envelope."""

    data: Any
    error: ErrorKind
    message: str
    status: int


class CookieValidationResult(TypedDict):
    valid: bool
    status: CookieStatus
    email_mask: str | None
    error: str | None


class _CheckinInfoRequired(TypedDict):
    is_sign: bool
    total_sign_day: int
    error: str | None


class CheckinInfoResult(_CheckinInfoRequired, total=False):
    retcode: int | None
    error_kind: ErrorKind | None


class _ActionRequired(TypedDict):
    success: bool
    message: str


class _CheckinRequired(_ActionRequired):
    status: CheckinStatus


class CheckinResult(_CheckinRequired, total=False):
    day: int | None
    retcode: int
    action_required: bool
    error_kind: ErrorKind | None


class RedeemResult(_ActionRequired, total=False):
    retcode: int
    error_kind: ErrorKind | None


CheckinResults = dict[str, dict[Game, CheckinResult]]
RedemptionResults = dict[str, dict[Game, dict[str, dict[str, RedeemResult]]]]
