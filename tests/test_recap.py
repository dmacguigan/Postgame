from sleeper_recap import enrich, recap
from tests.fixtures.week_data import (
    CONFIG,
    DRAFT_PICKS,
    LEAGUE,
    MATCHUPS,
    PLAYERS,
    ROSTERS,
    STATS,
    USERS,
)


def prompt():
    return recap.build_prompt(LEAGUE, USERS, ROSTERS, MATCHUPS, 2, CONFIG)


def extra_fixture():
    return {
        "players": PLAYERS,
        "stats": STATS,
        "draft_slots": enrich._draft_slots(DRAFT_PICKS),
        "pickups": [(4, "p6")],
        "prev_matchups": {},
        "team_streaks": {1: [(1, 100.0, "W"), (2, 110.0, "W")]},
        "hot_cold": {},
    }


def test_matchup_results_present():
    p = prompt()
    assert "Alice Attack" in p
    assert "130.5" in p and "90.25" in p
    assert "week 2" in p.lower()


def test_superlatives():
    p = prompt()
    # matchup 2 margin 1.5 is closest, matchup 1 margin 40.25 is blowout
    closest_idx = p.index("Closest game")
    assert "Dave Dynasty" in p[closest_idx:closest_idx + 200]
    blowout_idx = p.index("Biggest blowout")
    assert "Alice Attack" in p[blowout_idx:blowout_idx + 200]
    top_idx = p.index("Top scorer")
    assert "Alice Attack" in p[top_idx:top_idx + 100]


def test_owner_info_included_emails_excluded():
    p = prompt()
    assert "afraid of kickers" in p
    assert "Alice" in p
    assert "alice@example.com" not in p
    assert "@example.com" not in p


def test_tone_and_records():
    p = prompt()
    assert "light trash talk" in p
    assert "2-0" in p


def test_standings_numeric_sort():
    league = {"name": "Test League", "season": "2026", "total_rosters": 2}
    users = [
        {"user_id": "u1", "display_name": "team_a", "metadata": {"team_name": "Team A"}},
        {"user_id": "u2", "display_name": "team_b", "metadata": {"team_name": "Team B"}},
    ]
    rosters = [
        {"roster_id": 1, "owner_id": "u1", "settings": {"wins": 9, "losses": 1, "fpts": 300}},
        {"roster_id": 2, "owner_id": "u2", "settings": {"wins": 10, "losses": 0, "fpts": 290}},
    ]
    matchups = [
        {"roster_id": 1, "matchup_id": 1, "points": 150},
        {"roster_id": 2, "matchup_id": 1, "points": 140},
    ]
    config = {
        "league_id": "999",
        "tone": "test",
        "teams": {
            "1": {"team_name": "Team A", "owner_name": "A", "email": "a@test.com", "fun_facts": ""},
            "2": {"team_name": "Team B", "owner_name": "B", "email": "b@test.com", "fun_facts": ""},
        },
    }
    p = recap.build_prompt(league, users, rosters, matchups, 1, config)
    standings_idx = p.index("Season standings")
    standings_section = p[standings_idx:]
    team_b_idx = standings_section.index("Team B")
    team_a_idx = standings_section.index("Team A")
    assert team_b_idx < team_a_idx, "10-win team should appear before 9-win team in standings"


def test_extra_none_prompt_unchanged():
    assert prompt() == recap.build_prompt(LEAGUE, USERS, ROSTERS, MATCHUPS, 2, CONFIG, extra=None)


def test_extra_adds_matchup_details():
    p = recap.build_prompt(LEAGUE, USERS, ROSTERS, MATCHUPS, 2, CONFIG, extra=extra_fixture())
    assert "Matchup details:" in p


def test_extra_adds_roster_table_row_for_known_player():
    p = recap.build_prompt(LEAGUE, USERS, ROSTERS, MATCHUPS, 2, CONFIG, extra=extra_fixture())
    assert "| Alan Ace | QB | 27 | SF | R1.P3 | 200.0 | 2500 pass yd, 20 pass TD |" in p


def test_extra_marks_undrafted_player_waiver_fa():
    p = recap.build_prompt(LEAGUE, USERS, ROSTERS, MATCHUPS, 2, CONFIG, extra=extra_fixture())
    assert "waiver/FA" in p


def test_extra_form_guide_line():
    p = recap.build_prompt(LEAGUE, USERS, ROSTERS, MATCHUPS, 2, CONFIG, extra=extra_fixture())
    guide_idx = p.index("Recent results:")
    section = p[guide_idx:]
    assert "Alice Attack: last 2 weeks WW (100.0, 110.0)" in section
