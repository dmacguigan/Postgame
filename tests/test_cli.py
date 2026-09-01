import pytest

from sleeper_recap import cli, enrich, llm, sleeper
from tests.fixtures.week_data import LEAGUE, MATCHUPS, ROSTERS, USERS


_EMPTY_EXTRA = {
    "players": {},
    "stats": {},
    "draft_slots": {},
    "pickups": [],
    "prev_matchups": {},
    "team_streaks": {},
    "hot_cold": {},
}


def _patch_sleeper(monkeypatch):
    monkeypatch.setattr(sleeper, "league", lambda lid: LEAGUE)
    monkeypatch.setattr(sleeper, "users", lambda lid: USERS)
    monkeypatch.setattr(sleeper, "rosters", lambda lid: ROSTERS)
    monkeypatch.setattr(sleeper, "matchups", lambda lid, week: MATCHUPS)
    monkeypatch.setattr(sleeper, "nfl_state", lambda: {"week": 3})
    # keep enrichment offline in tests that don't care about it directly
    monkeypatch.setattr(enrich, "gather", lambda *args, **kwargs: dict(_EMPTY_EXTRA))


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
    cli.main(["recap", "--config", str(cfg), "--week", "2", "--provider", "anthropic", "--out", str(out)])
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


def test_recap_manual_writes_prompt(tmp_path, monkeypatch):
    _patch_sleeper(monkeypatch)

    def boom(*args):
        raise AssertionError("manual mode must not call llm.generate")

    monkeypatch.setattr(llm, "generate", boom)
    cfg = tmp_path / "config.toml"
    cli.main(["init", "--league-id", "999", "--config", str(cfg)])
    out = tmp_path / "p.md"
    cli.main(["recap", "--config", str(cfg), "--week", "2", "--provider", "manual", "--out", str(out)])
    text = out.read_text()
    assert "Copy everything below" in text
    assert "Alice Attack" in text


def test_recap_season_walks_chain(tmp_path, monkeypatch):
    _patch_sleeper(monkeypatch)
    leagues = {
        "999": {"name": "Test League", "season": "2026", "league_id": "999", "previous_league_id": "888"},
        "888": {"name": "Test League", "season": "2025", "league_id": "888", "previous_league_id": None},
    }
    monkeypatch.setattr(sleeper, "league", lambda lid: leagues[lid])
    seen = {}

    def fake_matchups(lid, week):
        seen["lid"] = lid
        return MATCHUPS

    monkeypatch.setattr(sleeper, "matchups", fake_matchups)
    cfg = tmp_path / "config.toml"
    cli.main(["init", "--league-id", "999", "--config", str(cfg)])
    cli.main(["recap", "--config", str(cfg), "--season", "2025", "--week", "3", "--out", str(tmp_path / "p.md")])
    assert seen["lid"] == "888"


def test_season_requires_week(tmp_path, monkeypatch):
    _patch_sleeper(monkeypatch)
    cfg = tmp_path / "config.toml"
    cli.main(["init", "--league-id", "999", "--config", str(cfg)])
    with pytest.raises(SystemExit, match="--week"):
        cli.main(["recap", "--config", str(cfg), "--season", "2025"])


def test_recap_degrades_gracefully_when_enrichment_fails(tmp_path, monkeypatch, capsys):
    _patch_sleeper(monkeypatch)

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(enrich, "gather", boom)
    monkeypatch.setattr(llm, "generate", lambda p, m, prompt: "Subject: Wow\n\nBody here")
    cfg = tmp_path / "config.toml"
    cli.main(["init", "--league-id", "999", "--config", str(cfg)])
    out = tmp_path / "email.md"
    cli.main(["recap", "--config", str(cfg), "--week", "2", "--provider", "anthropic", "--out", str(out)])
    captured = capsys.readouterr().out
    assert "warning: enrichment unavailable" in captured
    assert "boom" in captured
    assert out.read_text() == "Subject: Wow\n\nBody here"


def test_recap_includes_enrichment_when_gather_succeeds(tmp_path, monkeypatch):
    _patch_sleeper(monkeypatch)
    cfg = tmp_path / "config.toml"
    cli.main(["init", "--league-id", "999", "--config", str(cfg)])
    out = tmp_path / "p.md"
    cli.main(["recap", "--config", str(cfg), "--week", "2", "--provider", "manual", "--out", str(out)])
    assert "Matchup details:" in out.read_text()


def test_run_recap_returns_body_and_path(tmp_path, monkeypatch):
    _patch_sleeper(monkeypatch)
    monkeypatch.chdir(tmp_path)
    cfg = {"league_id": "999", "tone": "dry", "teams": {}}
    body, out = cli.run_recap(cfg, week=2, provider="manual")
    assert "Copy everything below" in body
    assert out == "recaps/week_2_prompt.md"
    assert (tmp_path / out).read_text(encoding="utf-8") == body
