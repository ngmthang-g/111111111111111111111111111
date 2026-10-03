from __future__ import annotations

# Exact constants recovered from the user-supplied TLMTool 2.1.2 Nuitka
# constants blobs (farm_data.py, pixel_data.py and FarmTab._sell_acc).
# Keep this module data-only. Do not "improve" values without new TLM evidence.

SELL_MAP_LIST: tuple[tuple[str, int], ...] = (
    ("Đại Lý", 2),
    ("Lạc Dương", 3),
    ("Tô Châu", 4),
    ("Lâu Lan", 5),
)

SELL_MAP_COORDS: dict[str, tuple[int, int]] = {
    "Đại Lý": (103, 188),
    "Lạc Dương": (231, 219),
    "Tô Châu": (191, 257),
    "Lâu Lan": (37, 126),
}

TRAIN_HEAL_COORDS: dict[str, tuple[int, int]] = {
    "Trị liệu Đại Lý": (43, 178),
    "Trị liệu Lạc Dương": (255, 126),
    "Trị liệu Tô Châu": (155, 252),
    "Trị liệu Lâu Lan": (294, 170),
}

TRUYEN_NPC_BY_TOWN: dict[int, int | tuple[int, int]] = {
    2: 45,
    3: 460,
    5: 387,
    4: (2, 45),
}

# FarmTab._sell_acc constants.
SELL_OPEN_CLICKS: tuple[tuple[int, int], ...] = (
    (888, 470),
    (473, 444),
)

SELL_CONFIRM_STEPS: tuple[tuple[int, int, str, str, str], ...] = (
    (138, 335, "donVang", "banVatPhamTab", "tab Bán Vật Phẩm"),
    (836, 147, "donVang", "trangBiTab", "tab Trang Bị"),
    (219, 641, "shop", "tickBanNhanh", "tick Bán Nhanh"),
)

SELL_CLOSE_CLICK = (1165, 110)
SELL_ERROR_CLOSE_CLICK = (1155, 110)
SELL_SLOT_TICK_SECONDS = 1.1
SELL_SLOT_CHECK_TIMEOUT = 0.3
SELL_SLOT_CHECK_INTERVAL = 0.05
SELL_MAX_SLOT_CLICKS = 100

# Exact relevant subset of pixel_data.PIXEL_DATA.
PIXEL_DATA: dict[str, dict[str, dict[str, object]]] = {
    "donVang": {
        "banVatPhamTab": {
            "region": (139, 305),
            "color": (143, 58, 21),
            "timeout": 1.0,
            "tolerance": 10,
        },
        "trangBiTab": {
            "region": (867, 141),
            "color": (255, 191, 10),
            "timeout": 1.0,
            "tolerance": 10,
        },
    },
    "shop": {
        "tuiDoTrong": {
            "region": (730, 190),
            "color": (209, 196, 173),
            "timeout": 1.0,
            "tolerance": 1,
        },
        "tuiDoTrong1": {
            "region": (795, 190),
            "color": (209, 196, 173),
            "timeout": 1.0,
            "tolerance": 1,
        },
        "tuiDoTrong2": {
            "region": (860, 190),
            "color": (209, 196, 173),
            "timeout": 1.0,
            "tolerance": 1,
        },
        "tuiDoTrong3": {
            "region": (925, 190),
            "color": (209, 196, 173),
            "timeout": 1.0,
            "tolerance": 1,
        },
        "tuiDoTrong4": {
            "region": (980, 190),
            "color": (209, 196, 173),
            "timeout": 1.0,
            "tolerance": 1,
        },
        "tuiDoTrong5": {
            "region": (1040, 190),
            "color": (209, 196, 173),
            "timeout": 1.0,
            "tolerance": 1,
        },
        "tuiDoTrong6": {
            "region": (1100, 190),
            "color": (209, 196, 173),
            "timeout": 1.0,
            "tolerance": 1,
        },
        "tickBanNhanh": {
            "region": (215, 648),
            "color": (150, 202, 68),
            "timeout": 1.0,
            "tolerance": 1,
        },
    },
}


def sell_map_names() -> tuple[str, ...]:
    return tuple(name for name, _map_id in SELL_MAP_LIST)


def sell_map_id(name: str) -> int:
    for map_name, map_id in SELL_MAP_LIST:
        if map_name == name:
            return map_id
    return 0


def sell_slot_pixel(index: int) -> tuple[str, tuple[int, int]]:
    """Recovered FarmTab rule: 0 -> tuiDoTrong, 1..6 -> tuiDoTrongN."""
    idx = max(0, min(6, int(index)))
    key = "tuiDoTrong" if idx == 0 else f"tuiDoTrong{idx}"
    region = PIXEL_DATA["shop"][key]["region"]
    return key, (int(region[0]), int(region[1]))
