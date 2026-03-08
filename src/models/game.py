"""Game models - Game Enum và Region configurations"""

import json
from dataclasses import dataclass
from enum import Enum

from src.config import PAGE_NAME_HOME_GAME
from src.constants import JSON_SEPARATORS


@dataclass(frozen=True)
class GameInfo:
    """Thông tin của 1 game - immutable."""

    code: str  # 'gs', 'sr', 'zzz'
    name: str  # Tên hiển thị
    game_id: str  # ID dùng trong API
    act_id: str  # Act ID cho check-in
    game_biz: str  # Game biz string
    signgame: str | None  # Signgame header (None cho Genshin)
    page_type: str = ""  # Type trang cụ thể (vd: ZZZ=46)

    def get_page_info(self, page_name: str = PAGE_NAME_HOME_GAME) -> str:
        """Sinh chuỗi JSON cho x-rpc-page_info với game_id và page_type động."""
        return json.dumps(
            {
                "pageName": page_name,
                "pageType": self.page_type,
                "pageId": "",
                "pageArrangement": "Hot" if page_name == PAGE_NAME_HOME_GAME else "",
                "gameId": self.game_id,
            },
            separators=JSON_SEPARATORS,
        )

    def get_sign_payload(self) -> dict:
        """Trả về Payload thiết lập mặc định theo đặc thù game."""
        # Genshin requires different json payload, while Star Rail and ZZZ use another structure.
        from src.config import RPC_LANGUAGE

        if self.signgame:  # Star Rail/ZZZ format.
            return {"act_id": self.act_id, "lang": RPC_LANGUAGE}
        return {"act_id": self.act_id}

    def get_sign_headers(self, account, page_info_name: str) -> dict:
        """Trả về Dictionary header mặc định."""
        from src.utils.helpers import build_rpc_headers

        # Lấy được class Game Enum chứ không phải model GameInfo vì Utils build_rpc_headers expect Enum Game.
        from src.models.game import Game

        matched_game = next(g for g in Game if g.value == self)

        headers = build_rpc_headers(
            account, "act_hoyolab", self.get_page_info(page_info_name), page_info_name, game=matched_game
        )
        if not self.signgame:
            # Genshin Impact specific sign headers
            headers["content-type"] = "application/json;charset=UTF-8"
            headers["x-rpc-app_version"] = ""
            headers["x-rpc-device_name"] = ""
        return headers


class Game(Enum):
    """Enum các game được hỗ trợ - Type-safe, IDE autocomplete"""

    GENSHIN = GameInfo(
        code="gs",
        name="Genshin Impact",
        game_id="2",
        act_id="e202102251931481",
        game_biz="hk4e_global",
        signgame=None,
    )
    STAR_RAIL = GameInfo(
        code="sr",
        name="Honkai: Star Rail",
        game_id="6",
        act_id="e202303301540311",
        game_biz="hkrpg_global",
        signgame="hkrpg",
    )
    ZZZ = GameInfo(
        code="zzz",
        name="Zenless Zone Zero",
        game_id="8",
        act_id="e202406031448091",
        game_biz="nap_global",
        signgame="zzz",
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
