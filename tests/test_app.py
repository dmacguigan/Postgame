import os
import re

import pytest

from sleeper_recap import app as appmod
from sleeper_recap import enrich, sleeper
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


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sleeper, "league", lambda lid: dict(LEAGUE, league_id=lid, previous_league_id=None))
    monkeypatch.setattr(sleeper, "users", lambda lid: USERS)
    monkeypatch.setattr(sleeper, "rosters", lambda lid: ROSTERS)
    monkeypatch.setattr(sleeper, "matchups", lambda lid, week: MATCHUPS)
    monkeypatch.setattr(sleeper, "nfl_state", lambda: {"week": 3})
    monkeypatch.setattr(enrich, "gather", lambda *a, **k: dict(_EMPTY_EXTRA))
    return appmod.create_app().test_client()


def test_index_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Postgame" in r.data


def test_leagues_empty_before_init(client):
    assert client.get("/api/leagues").get_json() == []


def test_icon_served(client):
    r = client.get("/icon.svg")
    assert r.status_code == 200
    assert b"<svg" in r.data


def test_config_400_before_init(client):
    r = client.get("/api/config?league_key=999")
    assert r.status_code == 400
    assert "Load" in r.get_json()["error"]


def test_init_then_get_config_and_leagues(client):
    r = client.post("/api/init", json={"league_id": "999"})
    assert r.status_code == 200
    assert r.get_json()["teams"]["1"]["team_name"] == "Alice Attack"
    assert client.get("/api/config?league_key=999").get_json()["league_id"] == "999"
    assert client.get("/api/leagues").get_json() == [{"key": "999", "name": "Test League", "platform": "sleeper"}]


def test_init_refuses_overwrite_without_force(client):
    cfg = client.post("/api/init", json={"league_id": "999"}).get_json()
    cfg["teams"]["1"]["owner_name"] = "Alice"
    client.post("/api/config", json=cfg)
    r = client.post("/api/init", json={"league_id": "999"})
    assert r.status_code == 409
    assert client.get("/api/config?league_key=999").get_json()["teams"]["1"]["owner_name"] == "Alice"
    r = client.post("/api/init", json={"league_id": "999", "force": True})
    assert r.status_code == 200
    assert r.get_json()["teams"]["1"]["owner_name"] == ""


def test_init_rejects_bad_id(client):
    r = client.post("/api/init", json={"league_id": "../x"})
    assert r.status_code == 400


def test_save_config(client):
    cfg = client.post("/api/init", json={"league_id": "999"}).get_json()
    cfg["teams"]["1"]["email"] = "a@example.com"
    cfg["tone"] = "dry"
    r = client.post("/api/config", json=cfg)
    assert r.status_code == 200
    assert r.get_json()["key"] == "999"
    assert client.get("/api/config?league_key=999").get_json()["teams"]["1"]["email"] == "a@example.com"


def test_seasons_walks_chain(client, monkeypatch):
    leagues = {
        "999": {"name": "T", "season": "2026", "league_id": "999", "previous_league_id": "888"},
        "888": {"name": "T", "season": "2025", "league_id": "888", "previous_league_id": None},
    }
    monkeypatch.setattr(sleeper, "league", lambda lid: leagues[lid])
    client.post("/api/init", json={"league_id": "999"})
    r = client.get("/api/seasons?league_key=999")
    assert r.get_json() == [
        {"season": "2026", "league_id": "999"},
        {"season": "2025", "league_id": "888"},
    ]


def test_generate_manual(client):
    cfg = client.post("/api/init", json={"league_id": "999"}).get_json()
    cfg["teams"]["1"]["email"] = "a@example.com"
    client.post("/api/config", json=cfg)
    r = client.post("/api/generate", json={"league_key": "999", "season": 2026, "week": 2})
    assert r.status_code == 200
    d = r.get_json()
    assert "Copy everything below" not in d["body"]
    assert d["body"].startswith("You are writing a weekly recap")
    assert d["out_path"].endswith(os.path.join("recaps", "999", "2026_week_2_prompt.md"))
    assert "recipients" not in d
    assert not re.search(r"[\w.]+@[\w.]+", d["body"])


def test_generate_no_scores_is_400(client, monkeypatch):
    zero = [dict(m, points=0) for m in MATCHUPS]
    monkeypatch.setattr(sleeper, "matchups", lambda lid, week: zero)
    client.post("/api/init", json={"league_id": "999"})
    r = client.post("/api/generate", json={"league_key": "999", "season": 2026, "week": 1})
    assert r.status_code == 400
    assert "no scores yet" in r.get_json()["error"]


def test_generate_without_config_is_400(client):
    r = client.post("/api/generate", json={"league_key": "999", "week": 2})
    assert r.status_code == 400
    assert "Load" in r.get_json()["error"]


def test_generate_rejects_non_numeric_season(client):
    client.post("/api/init", json={"league_id": "999"})
    r = client.post("/api/generate", json={"league_key": "999", "season": "../x", "week": 2})
    assert r.status_code == 400
    assert "numbers" in r.get_json()["error"]


def test_save_keeps_emails_from_cli(client):
    cfg = client.post("/api/init", json={"league_id": "999"}).get_json()
    cfg["teams"]["1"]["email"] = "a@example.com"
    client.post("/api/config", json=cfg)
    cfg = client.get("/api/config?league_key=999").get_json()
    cfg["teams"]["1"]["owner_name"] = "Alice"
    client.post("/api/config", json=cfg)
    assert client.get("/api/config?league_key=999").get_json()["teams"]["1"]["email"] == "a@example.com"


def test_espn_init_uses_key_and_hides_cookies(client, monkeypatch):
    from sleeper_recap import config as cfgmod

    seen = {}

    def fake_scaffold(league_id, platform="sleeper", espn_s2="", swid=""):
        seen.update(league_id=league_id, platform=platform, espn_s2=espn_s2, swid=swid)
        return {"league_id": league_id, "league_name": "E", "platform": platform,
                "espn_s2": espn_s2, "swid": swid, "teams": {}}

    monkeypatch.setattr(cfgmod, "scaffold", fake_scaffold)
    r = client.post("/api/init", json={"league_id": "42", "platform": "espn", "espn_s2": "s2", "swid": "{W}"})
    assert r.status_code == 200
    assert seen == {"league_id": "42", "platform": "espn", "espn_s2": "s2", "swid": "{W}"}
    d = r.get_json()
    assert d["key"] == "espn_42"
    assert "espn_s2" not in d and "swid" not in d
    assert client.get("/api/leagues").get_json() == [{"key": "espn_42", "name": "E", "platform": "espn"}]
    cfg = client.get("/api/config?league_key=espn_42").get_json()
    assert "espn_s2" not in cfg
    cfg["tone"] = "dry"
    client.post("/api/config", json=cfg)
    saved = cfgmod.load("leagues/espn_42.toml")
    assert saved["espn_s2"] == "s2" and saved["tone"] == "dry"


def test_bad_league_key_rejected(client):
    assert client.get("/api/config?league_key=../x").status_code == 400


def test_free_port_skips_busy_port():
    import socket

    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen(1)
        port = busy.getsockname()[1]
        assert appmod._free_port(port) == port + 1
