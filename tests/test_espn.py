import types

import pytest
from espn_api.requests.espn_requests import ESPNAccessDenied, ESPNInvalidLeague

from sleeper_recap import espn


def make_player(pid, name, position, pro_team, total=100.0, avg=10.0, stats=None):
    return types.SimpleNamespace(
        playerId=pid,
        name=name,
        position=position,
        proTeam=pro_team,
        total_points=total,
        avg_points=avg,
        stats=stats or {},
    )


def make_box_player(pid, name, position, pro_team, slot, points):
    return types.SimpleNamespace(
        playerId=pid,
        name=name,
        position=position,
        proTeam=pro_team,
        slot_position=slot,
        points=points,
        projected_points=points,
    )


def make_team(team_id, team_name, owners, wins, losses, points_for, roster):
    return types.SimpleNamespace(
        team_id=team_id,
        team_name=team_name,
        owners=owners,
        wins=wins,
        losses=losses,
        points_for=points_for,
        roster=roster,
    )


def make_league(teams, current_week=3, draft=None, box_scores=None, recent_activity=None, team_count=None):
    settings = types.SimpleNamespace(name="Fake League", team_count=team_count or len(teams))

    def _box_scores(week):
        if callable(box_scores):
            return box_scores(week)
        raise KeyError("season not started")

    def _recent_activity(size=25):
        if recent_activity is None:
            raise ESPNInvalidLeague("no activity endpoint")
        return recent_activity

    return types.SimpleNamespace(
        settings=settings,
        teams=teams,
        current_week=current_week,
        draft=draft or [],
        box_scores=_box_scores,
        recent_activity=_recent_activity,
    )


def build_client(monkeypatch, fake_league):
    monkeypatch.setattr(espn, "League", lambda **kwargs: fake_league)
    return espn.Client(league_id=123, season=2026)


def test_users_names_and_no_email(monkeypatch):
    team1 = make_team(1, "Alice Attack", [{"firstName": "Alice", "lastName": "Anderson", "displayName": "alice@example.com"}], 2, 0, 250.0, [])
    team2 = make_team(2, "Bob Bombers", [], 1, 1, 200.0, [])
    client = build_client(monkeypatch, make_league([team1, team2]))

    users = client.users()
    assert users[0] == {"user_id": "1", "display_name": "Alice Anderson", "metadata": {"team_name": "Alice Attack"}}
    assert users[1] == {"user_id": "2", "display_name": "Bob Bombers", "metadata": {"team_name": "Bob Bombers"}}
    for u in users:
        assert "@" not in u["display_name"]


def test_rosters(monkeypatch):
    p1 = make_player(101, "Alan Ace", "QB", "SF")
    team1 = make_team(1, "Alice Attack", [], 2, 0, 250.0, [p1])
    client = build_client(monkeypatch, make_league([team1]))

    rosters = client.rosters()
    assert rosters == [
        {
            "roster_id": 1,
            "owner_id": "1",
            "settings": {"wins": 2, "losses": 0, "fpts": 250.0},
            "players": ["101"],
        }
    ]


def test_matchups_pairs_and_bye(monkeypatch):
    team1 = make_team(1, "Team One", [], 1, 0, 100.0, [])
    team2 = make_team(2, "Team Two", [], 0, 1, 90.0, [])
    team3 = make_team(3, "Team Three", [], 1, 0, 80.0, [])

    lineup1 = [make_box_player(201, "Starter One", "QB", "SF", "QB", 20.0), make_box_player(202, "Bench One", "RB", "KC", "BE", 5.0)]
    lineup2 = [make_box_player(203, "Starter Two", "WR", "DAL", "WR", 15.0)]
    lineup3 = [make_box_player(204, "Bye Guy", "TE", "GB", "TE", 8.0)]

    box_pair = types.SimpleNamespace(
        home_team=team1, away_team=team2, home_score=25.0, away_score=15.0,
        home_lineup=lineup1, away_lineup=lineup2,
    )
    box_bye = types.SimpleNamespace(
        home_team=None, away_team=team3, home_score=0.0, away_score=8.0,
        home_lineup=[], away_lineup=lineup3,
    )

    client = build_client(monkeypatch, make_league([team1, team2, team3], box_scores=lambda week: [box_pair, box_bye]))
    result = client.matchups(league_id="123", week=1)

    assert len(result) == 3
    pair = [m for m in result if m["matchup_id"] == 1]
    assert len(pair) == 2
    ids = {m["roster_id"] for m in pair}
    assert ids == {1, 2}
    home = next(m for m in pair if m["roster_id"] == 1)
    assert home["starters"] == ["201"]
    assert home["players"] == ["201", "202"]
    assert home["players_points"] == {"201": 20.0, "202": 5.0}

    unpaired = [m for m in result if m["matchup_id"] == 2]
    assert len(unpaired) == 1
    assert unpaired[0]["roster_id"] == 3


def test_matchups_returns_empty_on_exception(monkeypatch):
    team1 = make_team(1, "Team One", [], 0, 0, 0.0, [])
    client = build_client(monkeypatch, make_league([team1]))
    assert client.matchups(league_id="123", week=1) == []


def test_draft_picks(monkeypatch):
    team1 = make_team(1, "Team One", [], 0, 0, 0.0, [])
    team2 = make_team(2, "Team Two", [], 0, 0, 0.0, [])
    pick1 = types.SimpleNamespace(playerId=301, playerName="Pick One", round_num=1, round_pick=1, team=team1)
    pick2 = types.SimpleNamespace(playerId=302, playerName="Pick Two", round_num=2, round_pick=1, team=team2)
    client = build_client(monkeypatch, make_league([team1, team2], draft=[pick1, pick2], team_count=2))

    picks = client.draft_picks(league_id="123")
    assert picks == [
        {"player_id": "301", "round": 1, "pick_no": 1},
        {"player_id": "302", "round": 2, "pick_no": 3},
    ]


def test_players_and_season_stats(monkeypatch):
    stats = {0: {"points": 100.0, "avg_points": 10.0, "breakdown": {"passingTouchdowns": 20.0, "rushingTouchdowns": 1.0, "receivingTouchdowns": 0.0}}}
    p1 = make_player(101, "Alan Ace", "QB", "SF", total=100.0, avg=10.0, stats=stats)
    team1 = make_team(1, "Team One", [], 0, 0, 0.0, [p1])
    client = build_client(monkeypatch, make_league([team1]))

    players = client.players()
    assert players["101"] == {"full_name": "Alan Ace", "position": "QB", "team": "SF", "age": None}

    season_stats = client.season_stats(2026)
    assert season_stats["101"] == {"pts_ppr": 100.0, "gp": 10, "pass_td": 20.0, "rush_td": 1.0, "rec_td": 0.0}


def test_access_denied_exits(monkeypatch):
    def raise_denied(**kwargs):
        raise ESPNAccessDenied("private")

    monkeypatch.setattr(espn, "League", raise_denied)
    with pytest.raises(SystemExit, match="private"):
        espn.Client(league_id=123, season=2026)


def test_invalid_league_exits(monkeypatch):
    def raise_invalid(**kwargs):
        raise ESPNInvalidLeague("nope")

    monkeypatch.setattr(espn, "League", raise_invalid)
    with pytest.raises(SystemExit, match="not found"):
        espn.Client(league_id=123, season=2026)


def test_transactions_empty_without_cookies(monkeypatch):
    team1 = make_team(1, "Team One", [], 0, 0, 0.0, [])
    client = build_client(monkeypatch, make_league([team1]))
    assert client.transactions(league_id="123", week=1) == []
