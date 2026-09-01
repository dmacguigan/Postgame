LEAGUE = {"name": "Test League", "season": "2026", "total_rosters": 4}

USERS = [
    {"user_id": "u1", "display_name": "alice_ff", "metadata": {"team_name": "Alice Attack"}},
    {"user_id": "u2", "display_name": "bob_ff", "metadata": {}},
    {"user_id": "u3", "display_name": "carol_ff", "metadata": {"team_name": "Carol Crush"}},
    {"user_id": "u4", "display_name": "dave_ff", "metadata": {}},
]

ROSTERS = [
    {"roster_id": 1, "owner_id": "u1", "settings": {"wins": 2, "losses": 0, "fpts": 250}},
    {"roster_id": 2, "owner_id": "u2", "settings": {"wins": 1, "losses": 1, "fpts": 220}},
    {"roster_id": 3, "owner_id": "u3", "settings": {"wins": 0, "losses": 2, "fpts": 180}},
    {"roster_id": 4, "owner_id": "u4", "settings": {"wins": 1, "losses": 1, "fpts": 210}},
]

MATCHUPS = [
    {"roster_id": 1, "matchup_id": 1, "points": 130.5},
    {"roster_id": 2, "matchup_id": 1, "points": 90.25},
    {"roster_id": 3, "matchup_id": 2, "points": 100.0},
    {"roster_id": 4, "matchup_id": 2, "points": 101.5},
]

CONFIG = {
    "league_id": "999",
    "provider": "anthropic",
    "tone": "funny, light trash talk",
    "teams": {
        "1": {"team_name": "Alice Attack", "owner_name": "Alice", "email": "alice@example.com", "fun_facts": "afraid of kickers"},
        "2": {"team_name": "Bob Bombers", "owner_name": "Bob", "email": "bob@example.com", "fun_facts": "drafts by jersey color"},
        "3": {"team_name": "Carol Crush", "owner_name": "Carol", "email": "carol@example.com", "fun_facts": ""},
        "4": {"team_name": "Dave Dynasty", "owner_name": "Dave", "email": "dave@example.com", "fun_facts": "three-time last place"},
    },
}
