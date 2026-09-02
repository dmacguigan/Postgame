import types

import pytest

from sleeper_recap import multiweek
from tests.fixtures.week_data import CONFIG, LEAGUE, MATCHUPS, PLAYERS, PREV_MATCHUPS, ROSTERS, TRANSACTIONS, USERS

WEEKS = {**PREV_MATCHUPS, 4: MATCHUPS, 5: [dict(m, points=0) for m in MATCHUPS]}


def fake_client(fail_tx=False):
    def tx(league_id, week):
        if fail_tx:
            raise RuntimeError("404")
        return TRANSACTIONS.get(week, [])

    return types.SimpleNamespace(
        league_id="999",
        league_obj=LEAGUE,
        matchups=lambda league_id, week: WEEKS.get(week, []),
        transactions=tx,
        players=lambda: PLAYERS,
        users=lambda league_id: USERS,
        rosters=lambda league_id: ROSTERS,
    )


def test_prompt_blocks():
    p = multiweek.build_prompt(fake_client(), 1, 5, CONFIG)
    assert "covering weeks 1-4" in p
    assert "| Alice Attack | 3-1 | 460.5 | 115.1 | 130.5 (wk 4) | 100.0 (wk 1) | 45.0 |" in p
    assert "Highest single-week score: Alice Attack 130.5 (week 4)" in p
    assert "Lowest single-week score: Carol Crush 80.0 (week 3)" in p
    assert "Biggest blowout: Alice Attack over Bob Bombers by 40.25 (week 4)" in p
    assert "Closest game: Dave Dynasty over Carol Crush by 1.5 (week 4)" in p
    assert "Longest win streak:" in p
    assert "Wk 4: Alice Attack 130.5 def Bob Bombers 90.25" in p
    assert "- Hattie Hot (Carol Crush): 133.0" in p
    assert "- Wade Waiver (Dave Dynasty, added week 3): 101.5 pts since" in p
    assert "Alan Ace" not in p.split("Waiver pickups")[1]
    assert "afraid of kickers" in p


def test_pickups_omitted_when_transactions_fail():
    p = multiweek.build_prompt(fake_client(fail_tx=True), 1, 4, CONFIG)
    assert "Waiver pickups" not in p
    assert "covering weeks 1-4" in p


def test_no_scored_weeks_errors():
    with pytest.raises(SystemExit, match="no scores"):
        multiweek.build_prompt(fake_client(), 5, 6, CONFIG)


def test_bad_range_errors():
    with pytest.raises(SystemExit, match="range"):
        multiweek.build_prompt(fake_client(), 3, 3, CONFIG)
