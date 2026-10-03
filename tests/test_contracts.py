from pathlib import Path

from tlmtool import __version__
from tlmtool.backend import Action, PerPidGate
from tlmtool.native_client import Command, Snapshot


def test_version_target():
    assert __version__ == "2.1.2"


def test_visible_action_surface_has_tlm_groups():
    required = {"login","reload","trung_ac","tang_bao_do","tri_lieu","train","ban_do","train_lsv","don_vang","rao","toi_uu"}
    assert required <= {x.value for x in Action}


def test_per_pid_gate_serializes_mutation():
    g = PerPidGate()
    assert g.try_enter(123)
    assert not g.try_enter(123)
    assert g.try_enter(456)
    g.leave(123)
    assert g.try_enter(123)


def test_no_hidden_developer_tabs_in_visible_ui_source():
    text = (Path(__file__).parents[1] / "src/tlmtool/app.py").read_text(encoding="utf-8")
    for label in ["ProxyTab", "EmuFarmTab", "DebugAndroidTab"]:
        assert label not in text


def test_snapshot_wire_field_order_matches_native_contract():
    assert [name for name, _ctype in Snapshot._fields_] == [
        "validMask", "roleID", "teamID", "level", "factionID",
        "hp", "maxHP", "mapID", "x", "y", "riding", "autoPathing",
        "mapReady", "waitingChangeMap", "dead", "autoFight",
        "freeBagSpace", "characterName",
    ]


def test_party_command_ids_are_locked():
    assert Command.PARTY_LEAVE == 34
    assert Command.PARTY_INVITE == 35
    assert Command.PARTY_JOIN == 36
    assert Command.REVIVE_NORMAL == 37
    assert Command.PARTY_CREATE == 38


def test_login_uses_tlm_fixed_100_row_model():
    text = (Path(__file__).parents[1] / "src/tlmtool/app.py").read_text(encoding="utf-8")
    assert "ROWS = 100" in text
    assert 'values=["Không", "Tool", "Proxy"]' in text


def test_native_party_surface_is_implemented_not_enum_only():
    text = (Path(__file__).parents[1] / "native/TlmSemanticBridge.cpp").read_text(encoding="utf-8")
    for case in ["PartyCreate", "PartyLeave", "PartyInvite", "PartyJoin", "ReviveNormal"]:
        assert f"case Command::{case}" in text


def test_post_login_dispatch_uses_tab_specific_workflows():
    text = (Path(__file__).parents[1] / "src/tlmtool/app.py").read_text(encoding="utf-8")
    start = text.index("    def _dispatch_after_login(self):")
    end = text.index("    def apply_schedule(self):", start)
    block = text[start:end]
    assert '"Party": (2, "toggle_run")' in block
    assert '"Train": (3, "_toggle_farm")' in block
    assert '"Train LSV": (4, "_toggle_farm")' in block
    assert '"Dồn vàng": (7, "_toggle_farm")' in block
    assert "self.action_all(action)" not in block


def test_party_after_action_uses_target_tab_workflow():
    text = (Path(__file__).parents[1] / "src/tlmtool/app.py").read_text(encoding="utf-8")
    start = text.index("    def _after_party_action(self):")
    end = text.index("    def stop(self):", start)
    block = text[start:end]
    assert '"Train": (3, "_toggle_farm")' in block
    assert '"Phó bản": (5, "_toggle_run")' in block
    assert "self.action_all(action)" not in block


def test_train_core_is_orchestrated_not_generic_action_only():
    text = (Path(__file__).parents[1] / "src/tlmtool/app.py").read_text(encoding="utf-8")
    start = text.index("class TrainTab(BaseTab):")
    end = text.index("class TrainLsvTab(BaseTab):", start)
    block = text[start:end]
    for method in [
        "def _refresh_accounts", "def _move_worker", "def _fight_worker",
        "def _farm_worker", "def _toggle_farm", "def _stop_all",
    ]:
        assert method in block
    assert 'start_bar(self, self._toggle_farm)' in block
    assert "lambda:self.action_all(Action.TRAIN)" not in block
    assert "ARRIVE_TOLERANCE = 40" in block


def test_native_bag_and_sell_surface_is_implemented():
    text = (Path(__file__).parents[1] / "native/TlmSemanticBridge.cpp").read_text(encoding="utf-8")
    for case in ["ReadBagPage", "SellBagItem"]:
        assert f"case Command::{case}" in text
    assert "NPCShop_SellItemTab" in text
    assert "RequestSellItem" in text
    assert "Item quest-family; chặn bán" in text


def test_semantic_driver_exposes_fresh_bag_sell_contract():
    text = (Path(__file__).parents[1] / "src/tlmtool/backend.py").read_text(encoding="utf-8")
    assert "def read_bag_page" in text
    assert "def sell_bag_item" in text
    assert "Command.READ_BAG_PAGE" in text
    assert "Command.SELL_BAG_ITEM" in text
    assert "def _split_i64" in text
