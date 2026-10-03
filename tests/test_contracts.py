from pathlib import Path

from tlmtool import __version__
from tlmtool.backend import Action, PerPidGate


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
