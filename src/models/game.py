"""Immutable supported-game metadata and region mappings."""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

GameCode = Literal["gs", "sr", "zzz"]


@dataclass(frozen=True)
class GameInfo:
    """Provider identifiers; HTTP request construction belongs to the adapter."""

    code: GameCode
    name: str
    short_name: str
    game_id: str
    act_id: str
    game_biz: str
    sign_game: str
    page_type: str = ""


class Game(Enum):
    """Enum các game được hỗ trợ - Type-safe, IDE autocomplete"""

    GENSHIN = GameInfo(
        code="gs",
        name="Genshin Impact",
        short_name="GI",
        game_id="2",
        act_id="e202102251931481",
        game_biz="hk4e_global",
        sign_game="hk4e",
    )
    STAR_RAIL = GameInfo(
        code="sr",
        name="Honkai: Star Rail",
        short_name="HSR",
        game_id="6",
        act_id="e202303301540311",
        game_biz="hkrpg_global",
        sign_game="hkrpg",
    )
    ZZZ = GameInfo(
        code="zzz",
        name="Zenless Zone Zero",
        short_name="ZZZ",
        game_id="8",
        act_id="e202406031448091",
        game_biz="nap_global",
        sign_game="zzz",
        page_type="46",  # Theo curl captured
    )


# Region codes theo từng game
REGIONS: dict[Game, dict[str, str]] = {
    Game.GENSHIN: {
        "asia": "os_asia",
        "usa": "os_usa",
        "euro": "os_euro",
        "tw": "os_cht",
    },
    Game.STAR_RAIL: {
        "asia": "prod_official_asia",
        "usa": "prod_official_usa",
        "euro": "prod_official_eur",
        "tw": "prod_official_cht",
    },
    Game.ZZZ: {
        "asia": "prod_gf_jp",
        "usa": "prod_gf_us",
        "euro": "prod_gf_eu",
        "tw": "prod_gf_sg",
    },
}


# ==================== REVERSE LOOKUPS ====================
# Derive từ Enum + REGIONS (single source) để map response API → model.
# Dùng cho fetch_all_uids: 1 request getUserGameRolesByLtoken trả về tất cả
# roles với (game_biz, region_value), cần map ngược về (Game, region_code).

# game_biz -> Game (vd "hkrpg_global" -> Game.STAR_RAIL)
GAME_BY_BIZ: dict[str, Game] = {game.value.game_biz: game for game in Game}

# (Game, region_value) -> region_code (vd (Game.ZZZ, "prod_gf_jp") -> "asia")
REGION_CODE_BY_VALUE: dict[tuple[Game, str], str] = {
    (game, region_value): region_code
    for game, regions in REGIONS.items()
    for region_code, region_value in regions.items()
}
