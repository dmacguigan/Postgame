from sleeper_recap import recap
from tests.fixtures.week_data import CONFIG, LEAGUE, MATCHUPS, ROSTERS, USERS


def prompt():
    return recap.build_prompt(LEAGUE, USERS, ROSTERS, MATCHUPS, 2, CONFIG)


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
