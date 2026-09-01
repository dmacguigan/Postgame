import tomllib

import pytest

from sleeper_recap import config, sleeper
from tests.fixtures.week_data import LEAGUE, ROSTERS, USERS


def _patch(monkeypatch):
    monkeypatch.setattr(sleeper, "league", lambda lid: LEAGUE)
    monkeypatch.setattr(sleeper, "users", lambda lid: USERS)
    monkeypatch.setattr(sleeper, "rosters", lambda lid: ROSTERS)


def test_scaffold_builds_teams(monkeypatch):
    _patch(monkeypatch)
    cfg = config.scaffold("999")
    assert cfg["league_id"] == "999"
    assert cfg["provider"] == "manual"
    assert cfg["league_name"] == "Test League"
    assert cfg["platform"] == "sleeper"
    assert "espn_s2" not in cfg
    assert cfg["teams"]["1"]["team_name"] == "Alice Attack"
    assert cfg["teams"]["2"]["team_name"] == "bob_ff"
    assert cfg["teams"]["1"]["owner_name"] == ""


def test_save_load_roundtrip(tmp_path, monkeypatch):
    _patch(monkeypatch)
    cfg = config.scaffold("999")
    cfg["tone"] = "dry"
    cfg["teams"]["1"]["owner_name"] = "Alice \U0001F600"
    cfg["teams"]["1"]["email"] = "a@example.com"
    path = tmp_path / "config.toml"
    config.save(str(path), cfg)
    assert config.load(str(path)) == cfg


def test_save_matches_cli_format(tmp_path, monkeypatch):
    _patch(monkeypatch)
    path = tmp_path / "config.toml"
    config.save(str(path), config.scaffold("999"))
    text = path.read_text(encoding="utf-8")
    assert 'league_id = "999"' in text
    assert "[teams.1]" in text
    assert 'owner_name = ""' in text


def test_load_missing_hints_init(tmp_path):
    with pytest.raises(SystemExit, match="init"):
        config.load(str(tmp_path / "nope.toml"))


def test_toml_str_roundtrips_emoji():
    name = "Team \U0001F600"
    parsed = tomllib.loads(f"x = {config._toml_str(name)}")
    assert parsed["x"] == name


def test_save_load_espn_fields(tmp_path):
    cfg = {"league_id": "1", "platform": "espn", "espn_s2": "abc", "swid": "{X}", "teams": {}}
    path = tmp_path / "c.toml"
    config.save(str(path), cfg)
    loaded = config.load(str(path))
    assert loaded["platform"] == "espn"
    assert loaded["espn_s2"] == "abc"
    assert loaded["swid"] == "{X}"
