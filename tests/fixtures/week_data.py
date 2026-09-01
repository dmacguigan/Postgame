LEAGUE = {"name": "Test League", "season": "2026", "total_rosters": 4}

USERS = [
    {"user_id": "u1", "display_name": "alice_ff", "metadata": {"team_name": "Alice Attack"}},
    {"user_id": "u2", "display_name": "bob_ff", "metadata": {}},
    {"user_id": "u3", "display_name": "carol_ff", "metadata": {"team_name": "Carol Crush"}},
    {"user_id": "u4", "display_name": "dave_ff", "metadata": {}},
]

ROSTERS = [
    {"roster_id": 1, "owner_id": "u1", "settings": {"wins": 2, "losses": 0, "fpts": 250}, "players": ["p1", "p2"]},
    {"roster_id": 2, "owner_id": "u2", "settings": {"wins": 1, "losses": 1, "fpts": 220}, "players": ["p3", "p5"]},
    {"roster_id": 3, "owner_id": "u3", "settings": {"wins": 0, "losses": 2, "fpts": 180}, "players": ["p4"]},
    {"roster_id": 4, "owner_id": "u4", "settings": {"wins": 1, "losses": 1, "fpts": 210}, "players": ["p6"]},
]

MATCHUPS = [
    {
        "roster_id": 1,
        "matchup_id": 1,
        "points": 130.5,
        "starters": ["p1"],
        "players": ["p1", "p2"],
        "players_points": {"p1": 130.5, "p2": 45.0},
    },
    {
        "roster_id": 2,
        "matchup_id": 1,
        "points": 90.25,
        "starters": ["p3"],
        "players": ["p3", "p5"],
        "players_points": {"p3": 90.25, "p5": 5.0},
    },
    {
        "roster_id": 3,
        "matchup_id": 2,
        "points": 100.0,
        "starters": ["p4"],
        "players": ["p4"],
        "players_points": {"p4": 100.0},
    },
    {
        "roster_id": 4,
        "matchup_id": 2,
        "points": 101.5,
        "starters": ["p6"],
        "players": ["p6"],
        "players_points": {"p6": 101.5},
    },
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

# enrichment fixtures
# p1 drafted, p2 bench scorer, p3 cold, p4 hot, p5 undrafted, p6 waiver add
PLAYERS = {
    "p1": {"full_name": "Alan Ace", "position": "QB", "age": 27, "team": "SF"},
    "p2": {"full_name": "Bree Bench", "position": "RB", "age": 24, "team": "KC"},
    "p3": {"full_name": "Cody Cold", "position": "WR", "age": 30, "team": "DAL"},
    "p4": {"full_name": "Hattie Hot", "position": "WR", "age": 23, "team": "GB"},
    "p5": {"full_name": "Undra Fted", "position": "TE", "age": 26, "team": "NE"},
    "p6": {"full_name": "Wade Waiver", "position": "RB", "age": 25, "team": "LAR"},
}

STATS = {
    "p1": {"pts_ppr": 200.0, "gp": 10, "pass_yd": 2500, "pass_td": 20, "rush_yd": 0, "rush_td": 0, "rec_yd": 0, "rec_td": 0},
    "p2": {"pts_ppr": 80.0, "gp": 10, "pass_yd": 0, "pass_td": 0, "rush_yd": 400, "rush_td": 3, "rec_yd": 100, "rec_td": 0},
    "p3": {"pts_ppr": 90.0, "gp": 9, "pass_yd": 0, "pass_td": 0, "rush_yd": 0, "rush_td": 0, "rec_yd": 700, "rec_td": 5},
    "p4": {"pts_ppr": 60.0, "gp": 10, "pass_yd": 0, "pass_td": 0, "rush_yd": 0, "rush_td": 0, "rec_yd": 500, "rec_td": 4},
    "p5": {"pts_ppr": 30.0, "gp": 6, "pass_yd": 0, "pass_td": 0, "rush_yd": 0, "rush_td": 0, "rec_yd": 150, "rec_td": 1},
    "p6": {"pts_ppr": 50.0, "gp": 10, "pass_yd": 0, "pass_td": 0, "rush_yd": 300, "rush_td": 2, "rec_yd": 0, "rec_td": 0},
}

DRAFT_PICKS = [
    {"player_id": "p1", "round": 1, "pick_no": 3, "roster_id": 1},
    {"player_id": "p2", "round": 4, "pick_no": 40, "roster_id": 1},
    {"player_id": "p3", "round": 2, "pick_no": 20, "roster_id": 2},
    {"player_id": "p4", "round": 3, "pick_no": 30, "roster_id": 3},
    {"player_id": "p6", "round": 5, "pick_no": 50, "roster_id": 4},
]

# keyed by week; one completed waiver add (p6), one trade to be skipped
TRANSACTIONS = {
    3: [
        {"type": "waiver", "status": "complete", "adds": {"p6": 4}, "drops": None},
    ],
    4: [
        {"type": "trade", "status": "complete", "adds": {"p1": 1}, "drops": {"p2": 2}},
    ],
}

# keyed by week; p4 hot (avg 11 vs 6.0 ppg), p3 cold (avg 3 vs 10.0 ppg), p2 sparse (1 appearance)
PREV_MATCHUPS = {
    1: [
        {"roster_id": 1, "matchup_id": 1, "points": 100.0, "players_points": {"p4": 12.0}},
        {"roster_id": 2, "matchup_id": 1, "points": 90.0, "players_points": {"p3": 2.0, "p2": 15.0}},
        {"roster_id": 3, "matchup_id": 2, "points": 95.0, "players_points": {}},
        {"roster_id": 4, "matchup_id": 2, "points": 105.0, "players_points": {}},
    ],
    2: [
        {"roster_id": 1, "matchup_id": 1, "points": 110.0, "players_points": {"p4": 10.0}},
        {"roster_id": 2, "matchup_id": 1, "points": 95.0, "players_points": {"p3": 3.0}},
        {"roster_id": 3, "matchup_id": 2, "points": 100.0, "players_points": {}},
        {"roster_id": 4, "matchup_id": 2, "points": 90.0, "players_points": {}},
    ],
    3: [
        {"roster_id": 1, "matchup_id": 1, "points": 120.0, "players_points": {"p4": 11.0}},
        {"roster_id": 2, "matchup_id": 1, "points": 130.0, "players_points": {"p3": 4.0}},
        {"roster_id": 3, "matchup_id": 2, "points": 80.0, "players_points": {}},
        {"roster_id": 4, "matchup_id": 2, "points": 85.0, "players_points": {}},
    ],
}
