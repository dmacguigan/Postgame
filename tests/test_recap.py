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
