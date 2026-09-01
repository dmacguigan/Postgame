import types

from sleeper_recap import enrich, recap
from tests.fixtures.week_data import (
    CONFIG,
    DRAFT_PICKS,
    LEAGUE,
    MATCHUPS,
    PLAYERS,
    PREV_MATCHUPS,
    ROSTERS,
    STATS,
    TRANSACTIONS,
    USERS,
)


def test_draft_slots_mapping():
    slots = enrich._draft_slots(DRAFT_PICKS)
    assert slots["p1"] == "R1.P3"
    assert "p5" not in slots


def test_bench_points_and_best_bench_via_build_prompt():
    extra = {
        "players": PLAYERS,
        "stats": STATS,
        "draft_slots": enrich._draft_slots(DRAFT_PICKS),
        "pickups": [],
        "prev_matchups": {},
        "team_streaks": {},
        "hot_cold": {},
    }
    p = recap.build_prompt(LEAGUE, USERS, ROSTERS, MATCHUPS, 2, CONFIG, extra=extra)
    assert "best bench: Bree Bench 45.0" in p
    assert "total bench points 45.0" in p


def test_team_streaks_paired_wl():
    streaks = enrich._team_streaks(PREV_MATCHUPS)
    assert streaks[1] == [(1, 100.0, "W"), (2, 110.0, "W"), (3, 120.0, "L")]
    assert streaks[2] == [(1, 90.0, "L"), (2, 95.0, "L"), (3, 130.0, "W")]


def test_hot_cold_flags_and_sparse_omitted():
    flags = enrich._hot_cold(MATCHUPS, PREV_MATCHUPS, STATS)
    assert flags["p4"] == "hot"
    assert flags["p3"] == "cold"
    assert "p2" not in flags


def test_gather_uses_injected_fake_sleeper_mod_no_network():
    fake = types.SimpleNamespace(
        players=lambda: PLAYERS,
        season_stats=lambda season: STATS,
        draft_picks=lambda league_id: DRAFT_PICKS,
        transactions=lambda league_id, week: TRANSACTIONS.get(week, []),
        matchups=lambda league_id, week: PREV_MATCHUPS.get(week, []),
    )
    extra = enrich.gather("999", "2026", 4, MATCHUPS, ROSTERS, sleeper_mod=fake)
    assert extra["players"] == PLAYERS
    assert extra["stats"] == STATS
    assert extra["draft_slots"]["p1"] == "R1.P3"
    assert extra["pickups"] == [(4, "p6")]
    assert set(extra["prev_matchups"].keys()) == {1, 2, 3}
    assert extra["team_streaks"][1][-1] == (3, 120.0, "L")
    assert extra["hot_cold"] == {"p3": "cold", "p4": "hot"}


def test_pickups_week_one_never_requests_week_zero():
    requested_weeks = []

    def fake_transactions(league_id, week):
        requested_weeks.append(week)
        return []

    fake = types.SimpleNamespace(
        players=lambda: PLAYERS,
        season_stats=lambda season: STATS,
        draft_picks=lambda league_id: DRAFT_PICKS,
        transactions=fake_transactions,
        matchups=lambda league_id, week: [],
    )
    enrich.gather("999", "2026", 1, MATCHUPS, ROSTERS, sleeper_mod=fake)
    assert requested_weeks == [1]
