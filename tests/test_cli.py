import tomllib

import pytest

from sleeper_recap import cli, llm, sleeper
from tests.fixtures.week_data import LEAGUE, MATCHUPS, ROSTERS, USERS


def _patch_sleeper(monkeypatch):
    monkeypatch.setattr(sleeper, "league", lambda lid: LEAGUE)
    monkeypatch.setattr(sleeper, "users", lambda lid: USERS)
    monkeypatch.setattr(sleeper, "rosters", lambda lid: ROSTERS)
    monkeypatch.setattr(sleeper, "matchups", lambda lid, week: MATCHUPS)
    monkeypatch.setattr(sleeper, "nfl_state", lambda: {"week": 3})


def test_init_writes_config(tmp_path, monkeypatch):
    _patch_sleeper(monkeypatch)
    cfg = tmp_path / "config.toml"
    cli.main(["init", "--league-id", "999", "--config", str(cfg)])
    text = cfg.read_text()
    assert 'league_id = "999"' in text
    assert "[teams.1]" in text
    assert "Alice Attack" in text
    assert 'owner_name = ""' in text


def test_init_refuses_overwrite(tmp_path, monkeypatch):
    _patch_sleeper(monkeypatch)
    cfg = tmp_path / "config.toml"
    cfg.write_text("existing")
    with pytest.raises(SystemExit, match="--force"):
        cli.main(["init", "--league-id", "999", "--config", str(cfg)])


def test_recap_writes_output(tmp_path, monkeypatch, capsys):
    _patch_sleeper(monkeypatch)
    monkeypatch.setattr(llm, "generate", lambda p, m, prompt: "Subject: Wow\n\nBody here")
    cfg = tmp_path / "config.toml"
    cli.main(["init", "--league-id", "999", "--config", str(cfg)])
    out = tmp_path / "email.md"
    cli.main(["recap", "--config", str(cfg), "--week", "2", "--out", str(out)])
    assert out.read_text() == "Subject: Wow\n\nBody here"
    captured = capsys.readouterr().out
    assert "Body here" in captured
    assert "Recipients:" in captured


def test_recap_default_week_from_state(tmp_path, monkeypatch):
    _patch_sleeper(monkeypatch)
    seen = {}

    def fake_matchups(lid, week):
        seen["week"] = week
        return MATCHUPS

    monkeypatch.setattr(sleeper, "matchups", fake_matchups)
    monkeypatch.setattr(llm, "generate", lambda p, m, prompt: "x")
    cfg = tmp_path / "config.toml"
    cli.main(["init", "--league-id", "999", "--config", str(cfg)])
    cli.main(["recap", "--config", str(cfg), "--out", str(tmp_path / "e.md")])
    assert seen["week"] == 2


def test_recap_no_scores_exits(tmp_path, monkeypatch):
    _patch_sleeper(monkeypatch)
    zero = [dict(m, points=0) for m in MATCHUPS]
    monkeypatch.setattr(sleeper, "matchups", lambda lid, week: zero)
    cfg = tmp_path / "config.toml"
    cli.main(["init", "--league-id", "999", "--config", str(cfg)])
    with pytest.raises(SystemExit, match="no scores yet"):
        cli.main(["recap", "--config", str(cfg), "--week", "1"])


def test_recap_missing_config_exits():
    with pytest.raises(SystemExit, match="init"):
        cli.main(["recap", "--config", "/nonexistent/config.toml"])


def test_toml_str_roundtrips_emoji():
    name = "Team \U0001F600"
    parsed = tomllib.loads(f"x = {cli._toml_str(name)}")
    assert parsed["x"] == name
