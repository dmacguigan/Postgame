import pytest

from sleeper_recap import platforms, sleeper
from tests.fixtures.week_data import LEAGUE, MATCHUPS

LEAGUES = {
    "999": {"name": "T", "season": "2026", "league_id": "999", "previous_league_id": "888"},
    "888": {"name": "T", "season": "2025", "league_id": "888", "previous_league_id": None},
}


def test_sleeper_walks_chain_and_lists_seasons(monkeypatch):
    monkeypatch.setattr(sleeper, "league", lambda lid: LEAGUES[lid])
    sp = platforms.open({"league_id": "999"}, season=2025)
    assert sp.league_id == "888"
    assert sp.league_obj["season"] == "2025"
    assert [s["season"] for s in platforms.open({"league_id": "999"}).seasons()] == ["2026", "2025"]


def test_sleeper_missing_season_exits(monkeypatch):
    monkeypatch.setattr(sleeper, "league", lambda lid: LEAGUES[lid])
    with pytest.raises(SystemExit, match="no 2020 season"):
        platforms.open({"league_id": "999"}, season=2020)


def test_sleeper_delegates_to_module(monkeypatch):
    monkeypatch.setattr(sleeper, "league", lambda lid: dict(LEAGUE, league_id=lid))
    monkeypatch.setattr(sleeper, "matchups", lambda lid, week: MATCHUPS)
    sp = platforms.open({"league_id": "999"})
    assert sp.league_id == "999"
    assert sp.matchups("999", 2) == MATCHUPS


def test_missing_league_id_exits():
    with pytest.raises(SystemExit, match="league_id"):
        platforms.open({})
